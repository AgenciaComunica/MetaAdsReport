from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
import unicodedata

import pandas as pd

from empresas.models import ConfiguracaoUploadEmpresa
from empresas.upload_config_services import (
    get_category_filter_enabled_map,
    get_enabled_chart_metric_keys,
    get_panel_metric_groups,
    get_enabled_table_metric_keys,
    read_uploaded_dataframe,
)
from concorrentes.models import ConcorrenteAd
from concorrentes.services import competitor_profiles

from .models import UploadPainel
from .services import campaign_table, summarize_metrics


PAID_TRAFFIC_HINTS = ('meta', 'facebook', 'instagram', 'ads', 'trafego', 'tráfego')
TRAFFIC_BLOCK_DEFINITIONS = [
    {
        'key': 'resultados',
        'title': 'Resultados',
        'description': 'Bloco principal de conversão, preparado para múltiplas plataformas e objetivos.',
        'metrics': ['resultado_principal', 'custo_por_resultado', 'taxa_resposta'],
        'chart_metrics': ['resultado_principal'],
        'highlighted': True,
    },
    {
        'key': 'custo_investimento',
        'title': 'Custo e Investimento',
        'description': 'Controle financeiro do período e eficiência básica do investimento.',
        'metrics': ['investimento', 'cpm', 'cpc', 'cpl'],
        'chart_metrics': ['investimento'],
        'highlighted': False,
    },
    {
        'key': 'performance_anuncios',
        'title': 'Performance dos Anúncios',
        'description': 'Entrega, alcance e capacidade de gerar ação ao longo do funil.',
        'metrics': ['impressoes', 'alcance', 'ctr', 'taxa_conversao', 'frequencia'],
        'chart_metrics': ['impressoes', 'alcance'],
        'highlighted': False,
    },
    {
        'key': 'qualidade_relevancia',
        'title': 'Qualidade e Relevância',
        'description': 'Leitura sintética da saúde do criativo e da pressão de mídia.',
        'metrics': ['score_relevancia', 'cpm_relativo'],
        'chart_metrics': ['score_relevancia'],
        'highlighted': False,
    },
]
TRAFFIC_METRIC_TOOLTIPS = {
    'investimento': 'Valor total investido em mídia no período selecionado.',
    'cpm': 'Custo médio para cada mil impressões entregues.',
    'cpc': 'Custo médio por clique gerado pelos anúncios.',
    'cpl': 'Custo por lead ou custo por resultado principal captado.',
    'impressoes': 'Quantidade total de exibições dos anúncios.',
    'alcance': 'Quantidade de pessoas únicas alcançadas.',
    'ctr': 'Percentual de cliques em relação às impressões.',
    'taxa_conversao': 'Percentual de resultados em relação aos cliques.',
    'frequencia': 'Média de vezes que cada pessoa impactada viu o anúncio.',
    'score_relevancia': 'Indicador sintético calculado com base em CTR, CPM, CPC e frequência.',
    'cpm_relativo': 'Compara o CPM atual com o período anterior. Abaixo de 1,00x é melhor.',
    'resultado_principal': 'Conversão principal do painel, genérica e preparada para diferentes objetivos.',
    'custo_por_resultado': 'Custo médio por conversão principal obtida.',
    'taxa_resposta': 'Percentual de respostas ou conversões em relação aos cliques gerados.',
}
TRAFFIC_POSITIVE_WHEN_HIGHER = {
    'impressoes',
    'alcance',
    'ctr',
    'taxa_conversao',
    'resultado_principal',
    'taxa_resposta',
    'score_relevancia',
}
TRAFFIC_POSITIVE_WHEN_LOWER = {
    'investimento',
    'cpm',
    'cpc',
    'cpl',
    'frequencia',
    'cpm_relativo',
    'custo_por_resultado',
}
TRAFFIC_PLAUSIBLE_VARIATION_LIMITS = {
    'investimento': Decimal('15'),
    'cpm': Decimal('12'),
    'cpc': Decimal('12'),
    'cpl': Decimal('15'),
    'impressoes': Decimal('15'),
    'alcance': Decimal('15'),
    'ctr': Decimal('10'),
    'taxa_conversao': Decimal('10'),
    'frequencia': Decimal('8'),
    'score_relevancia': Decimal('10'),
    'cpm_relativo': Decimal('10'),
    'resultado_principal': Decimal('15'),
    'custo_por_resultado': Decimal('15'),
    'taxa_resposta': Decimal('10'),
}
CRM_POSITIVE_WHEN_HIGHER = {
    'receita_total',
    'vendas_concluidas',
    'taxa_conversao',
    'conversas',
    'ticket_medio',
    'receita_marketing_pago',
    'receita_marketing_organico',
    'receita_operacional',
    'receita_sem_categoria',
    'presenca_digital_visualizacoes_totais',
    'presenca_digital_alcance_total',
    'presenca_digital_visualizacoes_redes',
    'presenca_digital_impressoes_trafego',
    'presenca_fisica_leads_presenciais',
    'presenca_fisica_oportunidades_presenciais',
    'atendimento_conversas_trafego_pago',
    'atendimento_conversas_organicas',
    'atendimento_taxa_conversao',
    'resultado_vendas_marketing',
    'resultado_receita_marketing',
    'resultado_vendas_operacao',
    'resultado_receita_operacao',
}
CRM_PLAUSIBLE_VARIATION_LIMITS = {
    'receita_total': Decimal('15'),
    'vendas_concluidas': Decimal('15'),
    'taxa_conversao': Decimal('10'),
    'conversas': Decimal('15'),
    'ticket_medio': Decimal('12'),
    'receita_marketing_pago': Decimal('15'),
    'receita_marketing_organico': Decimal('15'),
    'receita_operacional': Decimal('15'),
    'receita_sem_categoria': Decimal('15'),
    'presenca_digital_visualizacoes_totais': Decimal('15'),
    'presenca_digital_alcance_total': Decimal('15'),
    'presenca_digital_visualizacoes_redes': Decimal('15'),
    'presenca_digital_impressoes_trafego': Decimal('15'),
    'presenca_fisica_leads_presenciais': Decimal('15'),
    'presenca_fisica_oportunidades_presenciais': Decimal('15'),
    'atendimento_conversas_trafego_pago': Decimal('15'),
    'atendimento_conversas_organicas': Decimal('15'),
    'atendimento_taxa_conversao': Decimal('10'),
    'resultado_vendas_marketing': Decimal('15'),
    'resultado_receita_marketing': Decimal('15'),
    'resultado_vendas_operacao': Decimal('15'),
    'resultado_receita_operacao': Decimal('15'),
}
SOCIAL_POSITIVE_WHEN_HIGHER = {
    'quantidade_publicacoes',
    'visualizacoes',
    'alcance',
    'curtidas',
    'compartilhamentos',
    'quantidade_posts',
    'visualizacoes_posts',
    'alcance_posts',
    'curtidas_posts',
    'compartilhamentos_posts',
    'quantidade_stories',
    'visualizacoes_stories',
    'alcance_stories',
    'curtidas_stories',
    'compartilhamentos_stories',
    'comentarios',
    'salvamentos',
    'respostas',
    'cliques_link',
    'visitas_perfil',
    'seguimentos',
    'usuarios',
    'novos_usuarios',
    'sessoes',
    'sessoes_engajadas',
    'visualizacoes_pagina',
    'taxa_engajamento',
    'conversoes',
}
SOCIAL_PLAUSIBLE_VARIATION_LIMITS = {key: Decimal('15') for key in SOCIAL_POSITIVE_WHEN_HIGHER}
CRM_STATUS_COLOR_MAP = {
    'venda concluida': '#2d6a4f',
    'venda concluída': '#2d6a4f',
    'retorno': '#175cd3',
    'ausência de resposta': '#6b7280',
    'ausencia de resposta': '#6b7280',
    'pedido com +10 peças': '#0f766e',
    'conhecimento com preço menor': '#f59e0b',
    'cliente indeciso': '#7c3aed',
    'indisponibilidade de data': '#0ea5e9',
    'apenas passar valores': '#f97316',
    'demora no atendimento': '#dc2626',
    'fora do escopo': '#92400e',
    'relação 0 - sem venda': '#475569',
    'falta de identificação da necessidade no interesse': '#b45309',
    'interação interna': '#4f46e5',
    'não informado': '#94a3b8',
}
CRM_STATUS_COLOR_RULES = [
    ('venda concluida', '#16A34A'),
    ('retorno', '#2563EB'),
    ('ausencia de resposta', '#9CA3AF'),
    ('pedido com', '#F97316'),
    ('nao aprovou o valor', '#DC2626'),
    ('concorrente com preco menor', '#7C3AED'),
    ('cliente indeciso', '#FACC15'),
    ('indisponibilidade de data', '#0ea5e9'),
    ('apenas saber valores', '#14B8A6'),
    ('demora no atendimento', '#FB7185'),
    ('fora do escopo', '#A855F7'),
    ('reacao ig', '#A855F7'),
    ('recusa de identificacao da marca clone', '#D97706'),
    ('interacao interna', '#334155'),
    ('nao informado', '#94a3b8'),
]
LEAD_TEMPERATURE_COLOR_RULES = [
    ('cliente', '#16A34A'),
    ('muito quente', '#A855F7'),
    ('quente', '#DC2626'),
    ('frio', '#2563EB'),
    ('nao informado', '#94A3B8'),
]
LEAD_TEMPERATURE_DISPLAY_ORDER = ['Cliente', 'Muito Quente', 'Quente', 'Frio', 'Não informado']


def build_dashboard_upload_tabs(
    empresa,
    traffic_queryset,
    period_start=None,
    period_end=None,
    previous_start=None,
    previous_end=None,
    previous_queryset=None,
    active_key=None,
):
    configs = list(empresa.configuracoes_upload.all())
    traffic_has_data = traffic_queryset.exists()
    tabs = []
    has_tabs = bool(configs)
    if has_tabs:
        complete_tab = _empty_tab('analise_completa', 'Resumo Executivo')
        complete_tab.update({'configured': True, 'description': 'Painel cruzado geral entre presença digital, atendimento e resultado.'})
        if active_key == 'analise_completa':
            traffic_config = next(
                (config for config in configs if config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO),
                None,
            )
            crm_config = next(
                (config for config in configs if config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.CRM_VENDAS),
                None,
            )
            leads_configs = [config for config in configs if config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS]
            social_configs = [config for config in configs if config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS]
            complete_tab = build_complete_analysis_tab_from_configs(
                traffic_config,
                crm_config,
                leads_configs,
                social_configs,
                traffic_queryset,
                previous_queryset=previous_queryset,
                period_start=period_start,
                period_end=period_end,
                previous_start=previous_start,
                previous_end=previous_end,
            )
        tabs.append(complete_tab)
    for config in configs:
        key = f'{config.tipo_documento}_{config.pk}'
        tab = _build_tab_stub(config, traffic_has_data, key)
        if key == active_key:
            if config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO:
                tab = build_traffic_tab(config, traffic_queryset, previous_queryset=previous_queryset, key=key)
            elif config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.CRM_VENDAS:
                tab = build_crm_tab(
                    config,
                    period_start,
                    period_end,
                    previous_start=previous_start,
                    previous_end=previous_end,
                    key=key,
                )
            elif config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS:
                tab = build_leads_tab(config, period_start, period_end, key=key)
            elif config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS:
                tab = build_social_tab(
                    config,
                    period_start,
                    period_end,
                    previous_start=previous_start,
                    previous_end=previous_end,
                    key=key,
                )
        tabs.append(tab)
    return tabs


def _build_tab_stub(config, traffic_has_data, key):
    if config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO:
        ready = bool(config) and traffic_has_data
    elif config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS:
        ready = True
    elif config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS:
        ready = True
    else:
        ready = bool(config.mapeamento_json)
    return {
        'key': key,
        'panel_type': config.tipo_documento,
        'title': config.nome,
        'config_id': config.pk,
        'configured': True,
        'ready': ready,
        'config_name': config.nome,
        'description': '',
    }


def build_traffic_tab(config, queryset, previous_queryset=None, key='trafego_pago'):
    summary = summarize_metrics(queryset)
    previous_summary = summarize_metrics(previous_queryset) if previous_queryset is not None else {}
    result_label = _resolve_result_label(config)
    derived_metrics = _build_traffic_metric_values(summary, previous_summary)
    metric_definitions = _build_traffic_metric_definitions(result_label)
    selected_table_keys = get_enabled_table_metric_keys(config.tipo_documento, config.metricas_painel_json) if config else []
    selected_chart_keys = get_enabled_chart_metric_keys(config.tipo_documento, config.metricas_painel_json) if config else []
    filter_enabled_map = get_category_filter_enabled_map(config.tipo_documento, config.metricas_painel_json) if config else {}
    previous_metrics = _build_traffic_metric_values(previous_summary, {})
    block_cards = _build_traffic_blocks(derived_metrics, previous_metrics, metric_definitions, selected_table_keys, filter_enabled_map)
    all_chart_keys = []
    for block_def in TRAFFIC_BLOCK_DEFINITIONS:
        keys = [k for k in block_def.get('chart_metrics', []) if k in set(selected_chart_keys)]
        if not keys:
            keys = [k for k in block_def.get('chart_metrics', []) if k in set(selected_table_keys)]
        all_chart_keys.extend(k for k in keys if k not in all_chart_keys)
    tab_chart = _build_traffic_line_chart(config.empresa if config else None, 'traffic_combined', all_chart_keys, metric_definitions) if config and getattr(config, 'empresa', None) else None
    return {
        'key': key,
        'panel_type': ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO,
        'title': config.nome if config else 'Tráfego Pago',
        'config_id': config.pk if config else None,
        'configured': bool(config),
        'ready': bool(config) and queryset.exists(),
        'config_name': config.nome if config else '',
        'description': 'Dados consolidados do dashboard atual de campanhas.',
        'kpis': summary,
        'result_label': result_label,
        'metric_blocks': block_cards,
        'tab_chart': tab_chart,
        'campaign_rows': campaign_table(queryset),
    }


def build_crm_tab(config, period_start=None, period_end=None, previous_start=None, previous_end=None, key='crm_vendas'):
    if not config:
        return _empty_tab('crm_vendas', 'Vendas')
    all_rows = _read_mapped_rows(config, date_key='data_contato')
    rows = _filter_rows_by_period(all_rows, period_start, period_end, 'data_contato')
    previous_rows = _filter_rows_by_period(all_rows, previous_start, previous_end, 'data_contato')
    closed_status = {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}
    selected_table_keys = set(get_enabled_table_metric_keys(config.tipo_documento, config.metricas_painel_json))
    selected_chart_keys = set(get_enabled_chart_metric_keys(config.tipo_documento, config.metricas_painel_json))
    filter_enabled_map = get_category_filter_enabled_map(config.tipo_documento, config.metricas_painel_json)
    current_summary = _crm_period_summary(rows, closed_status, config)
    previous_summary = _crm_period_summary(previous_rows, closed_status, config)
    resultado_metrics = [
        ('receita_total', 'Receita Total', True, ''),
        ('vendas_concluidas', 'Vendas Concluídas', False, ''),
        ('taxa_conversao', 'Taxa de Conversão', False, '%'),
        ('conversas', 'Conversas', False, ''),
        ('ticket_medio', 'Ticket Médio', True, ''),
    ]
    tab_chart = _build_origem_stacked_area_chart(all_rows, config)
    category_blocks = _build_crm_category_blocks(
        selected_table_keys,
        selected_chart_keys,
        current_summary,
        previous_summary,
        filter_enabled_map,
        all_rows=all_rows,
        config=config,
    )
    return {
        'key': key,
        'panel_type': ConfiguracaoUploadEmpresa.TipoDocumento.CRM_VENDAS,
        'title': config.nome,
        'config_id': config.pk,
        'configured': True,
        'ready': bool(config.mapeamento_json),
        'config_name': config.nome,
        'description': 'Leitura do arquivo configurado para CRM e vendas.',
        'rows': rows[:20],
        'kpis': current_summary['geral'],
        'tab_chart': tab_chart,
        'category_blocks': category_blocks,
    }


def build_leads_tab(config, period_start=None, period_end=None, key='leads_eventos'):
    if not config:
        return _empty_tab('leads_eventos', 'Presença Física')
    rows = []
    chart_categories = []
    chart_series = []
    current_entries = []
    for entry in config.eventos_painel.all():
        if period_start and entry.data_evento < period_start:
            continue
        if period_end and entry.data_evento > period_end:
            continue
        current_entries.append(entry)
        rows.append(
            {
                'evento': entry.nome_evento,
                'data_evento': entry.data_evento,
                'impacto': entry.get_impacto_display(),
                'leads_media': entry.leads_media,
            }
        )
        chart_categories.append(entry.nome_evento)
        chart_series.append(entry.leads_media)
    kpis = {
        'eventos_total': len(current_entries),
        'participantes_total': sum(entry.leads_media for entry in current_entries),
    }
    return {
        'key': key,
        'panel_type': ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS,
        'title': config.nome,
        'config_id': config.pk,
        'configured': True,
        'ready': True,
        'config_name': config.nome,
        'description': 'Entradas manuais de eventos com impacto e média de pessoas alcançadas.',
        'rows': rows[:50],
        'kpis': kpis,
        'tab_chart': _build_leads_monthly_line_chart(config, key=f'leads_{key}'),
    }


def build_social_tab(config, period_start=None, period_end=None, previous_start=None, previous_end=None, key='redes_sociais'):
    if not config:
        return _empty_tab('redes_sociais', 'Presença Digital')
    digital_type = _get_social_digital_type(config)
    all_rows = _read_social_rows(config)
    rows = _filter_rows_by_period(all_rows, period_start, period_end, 'data_publicacao')
    selected_table_keys = set(get_enabled_table_metric_keys(config.tipo_documento, config.metricas_painel_json, variant=digital_type))
    selected_chart_keys = set(get_enabled_chart_metric_keys(config.tipo_documento, config.metricas_painel_json, variant=digital_type))
    filter_enabled_map = get_category_filter_enabled_map(config.tipo_documento, config.metricas_painel_json, variant=digital_type)
    current_summary = _social_period_summary(rows, digital_type=digital_type)
    previous_rows = _filter_rows_by_period(all_rows, previous_start, previous_end, 'data_publicacao')
    previous_summary = _social_period_summary(previous_rows, digital_type=digital_type)
    definitions = _get_social_block_definitions(digital_type)
    combined_chart_keys = []
    combined_metric_defs = []
    for _, _, _, metric_defs, chart_defaults in definitions:
        keys = [k for k in chart_defaults if k in selected_chart_keys]
        if not keys:
            keys = [item[0] for item in metric_defs if item[0] in selected_table_keys]
        for k in keys:
            if k not in combined_chart_keys:
                combined_chart_keys.append(k)
        for item in metric_defs:
            if item[0] in combined_chart_keys and item not in combined_metric_defs:
                combined_metric_defs.append(item)
    tab_chart = _build_social_monthly_line_chart(all_rows, digital_type, 'social_combined', combined_metric_defs, combined_chart_keys)
    category_blocks = _build_social_category_blocks(digital_type, selected_table_keys, selected_chart_keys, current_summary, previous_summary, filter_enabled_map)
    return {
        'key': key,
        'panel_type': ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS,
        'title': config.nome,
        'config_id': config.pk,
        'configured': True,
        'ready': True,
        'config_name': config.nome,
        'description': _social_tab_description(digital_type),
        'rows': rows[:20],
        'tab_chart': tab_chart,
        'category_blocks': category_blocks,
    }


def build_complete_analysis_tab(traffic_tab, crm_tab, leads_tab):
    investment = traffic_tab['kpis'].get('investimento') or Decimal('0')
    crm_rows = crm_tab.get('rows') or []
    paid_crm_rows = [row for row in crm_rows if _is_paid_traffic_sale(row)]
    paid_revenue = sum((_to_decimal(row.get('valor_venda')) for row in paid_crm_rows), Decimal('0'))
    total_revenue = crm_tab.get('kpis', {}).get('receita_total') or Decimal('0')
    roas = (paid_revenue / investment) if investment else Decimal('0')
    return {
        'key': 'analise_completa',
        'panel_type': 'analise_completa',
        'title': 'Resumo Executivo',
        'configured': True,
        'ready': traffic_tab['ready'] or crm_tab['ready'] or leads_tab['ready'],
        'description': 'Cruza investimento de tráfego pago com o CRM e os leads de eventos disponíveis.',
        'kpis': {
            'investimento_trafego': investment,
            'receita_crm_total': total_revenue,
            'receita_trafego_estimada': paid_revenue,
            'roas_estimado': roas,
            'vendas_trafego_estimada': len(paid_crm_rows),
            'leads_eventos': leads_tab.get('kpis', {}).get('leads_total', 0),
        },
        'insights': [
            f'Investimento atual em tráfego pago: R$ {investment:.2f}',
            f'Receita total no CRM: R$ {total_revenue:.2f}',
            f'Receita estimada de leads marcados como tráfego pago: R$ {paid_revenue:.2f}',
            f'ROAS estimado com base no CRM: {roas:.2f}x' if investment else 'ROAS estimado indisponível sem investimento em tráfego pago.',
        ],
    }


def build_complete_analysis_tab_from_configs(
    traffic_config,
    crm_config,
    leads_configs,
    social_configs,
    traffic_queryset,
    previous_queryset=None,
    period_start=None,
    period_end=None,
    previous_start=None,
    previous_end=None,
):
    leads_configs = leads_configs or []
    social_configs = social_configs or []
    traffic_summary = summarize_metrics(traffic_queryset)
    previous_traffic_summary = summarize_metrics(previous_queryset) if previous_queryset is not None else {}
    all_crm_rows_raw = _read_mapped_rows(crm_config, date_key='data_contato') if crm_config else []
    crm_rows = _filter_rows_by_period(all_crm_rows_raw, period_start, period_end, 'data_contato')
    previous_crm_rows = _filter_rows_by_period(all_crm_rows_raw, previous_start, previous_end, 'data_contato')
    crm_summary = _crm_period_summary(crm_rows, {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}, crm_config) if crm_config else {'geral': {}, 'origem': {}}
    previous_crm_summary = _crm_period_summary(previous_crm_rows, {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}, crm_config) if crm_config else {'geral': {}, 'origem': {}}
    leads_rows = []
    previous_leads_rows = []
    for config in leads_configs:
        leads_rows.extend(_filter_leads_event_entries(config, period_start, period_end))
        previous_leads_rows.extend(_filter_leads_event_entries(config, previous_start, previous_end))
    social_rows = []
    previous_social_rows = []
    social_summaries = []
    previous_social_summaries = []
    for config in social_configs:
        digital_type = _get_social_digital_type(config)
        _all_config_social_rows = _read_social_rows(config)
        current_rows = _filter_rows_by_period(_all_config_social_rows, period_start, period_end, 'data_publicacao')
        previous_rows = _filter_rows_by_period(_all_config_social_rows, previous_start, previous_end, 'data_publicacao')
        social_rows.extend(current_rows)
        previous_social_rows.extend(previous_rows)
        social_summaries.append((config, _social_period_summary(current_rows, digital_type=digital_type)))
        previous_social_summaries.append((config, _social_period_summary(previous_rows, digital_type=digital_type)))
    social_summary = _aggregate_social_summaries([item[1] for item in social_summaries]) if social_configs else {}
    previous_social_summary = _aggregate_social_summaries([item[1] for item in previous_social_summaries]) if social_configs else {}
    leads_summaries = [(config, _leads_event_period_summary(_filter_leads_event_entries(config, period_start, period_end))) for config in leads_configs]
    previous_leads_summaries = [(config, _leads_event_period_summary(_filter_leads_event_entries(config, previous_start, previous_end))) for config in leads_configs]
    leads_summary = _leads_event_period_summary(leads_rows) if leads_configs else {}
    previous_leads_summary = _leads_event_period_summary(previous_leads_rows) if leads_configs else {}
    competitor_signals = _build_competitor_signals(traffic_config.empresa if traffic_config else (crm_config.empresa if crm_config else (social_configs[0].empresa if social_configs else None)))

    marketing_rows = [row for row in crm_rows if _is_marketing_sale(row, crm_config)]
    previous_marketing_rows = [row for row in previous_crm_rows if _is_marketing_sale(row, crm_config)]
    operacao_rows = [row for row in crm_rows if _is_operacao_or_sem_categoria_sale(row, crm_config)]
    previous_operacao_rows = [row for row in previous_crm_rows if _is_operacao_or_sem_categoria_sale(row, crm_config)]
    current_operacao_marketing_share = _calculate_combined_marketing_share(social_summaries, leads_summaries)
    previous_operacao_marketing_share = _calculate_combined_marketing_share(previous_social_summaries, previous_leads_summaries)
    marketing_revenue = sum((_to_decimal(row.get('valor_venda')) for row in marketing_rows), Decimal('0'))
    previous_marketing_revenue = sum((_to_decimal(row.get('valor_venda')) for row in previous_marketing_rows), Decimal('0'))
    operacao_revenue = sum((_to_decimal(row.get('valor_venda')) for row in operacao_rows), Decimal('0'))
    previous_operacao_revenue = sum((_to_decimal(row.get('valor_venda')) for row in previous_operacao_rows), Decimal('0'))
    marketing_revenue += operacao_revenue * current_operacao_marketing_share
    previous_marketing_revenue += previous_operacao_revenue * previous_operacao_marketing_share
    operacao_revenue -= operacao_revenue * current_operacao_marketing_share
    previous_operacao_revenue -= previous_operacao_revenue * previous_operacao_marketing_share
    marketing_sales = sum(1 for row in marketing_rows if _crm_is_closed_sale(row, {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}))
    previous_marketing_sales = sum(1 for row in previous_marketing_rows if _crm_is_closed_sale(row, {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}))
    operacao_sales = sum(1 for row in operacao_rows if _crm_is_closed_sale(row, {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}))
    previous_operacao_sales = sum(1 for row in previous_operacao_rows if _crm_is_closed_sale(row, {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}))

    # Monthly charts for executive summary panels
    empresa = (
        traffic_config.empresa if traffic_config and getattr(traffic_config, 'empresa', None)
        else (crm_config.empresa if crm_config and getattr(crm_config, 'empresa', None)
              else (social_configs[0].empresa if social_configs else None))
    )
    all_crm_rows = all_crm_rows_raw

    _exec_closed_status = {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}

    def _exec_monthly_crm_chart(chart_key, series_builders):
        """series_builders: list of (name, fn(monthly_summary) -> float)"""
        groups = _group_rows_by_month(all_crm_rows, 'data_contato')
        month_keys = _last_n_months(12)
        active = [mk for mk in month_keys if mk in groups]
        if not active:
            return None
        cats = [_short_month_label(y, m) for y, m in active]
        series = []
        for name, fn in series_builders:
            data = []
            for mk in active:
                ms = _crm_period_summary(groups[mk], _exec_closed_status, crm_config)
                data.append(_decimal_to_float(_to_decimal(fn(ms))))
            series.append({'name': name, 'data': data})
        return {'key': chart_key, 'title': 'Evolução Mensal', 'categories': cats, 'series': series}

    # Build single combined line chart for executive summary
    tab_chart_series = []
    tab_chart_categories = None

    if empresa:
        monthly_traffic = _build_monthly_traffic_data(empresa)
        month_keys_exec = _last_n_months(12)
        active_exec = [mk for mk in month_keys_exec if mk in monthly_traffic]
        if active_exec:
            tab_chart_categories = [_short_month_label(y, m) for y, m in active_exec]
            tab_chart_series.append({'name': 'Alcance (Tráfego)', 'data': [_decimal_to_float(monthly_traffic[mk].get('alcance', 0)) for mk in active_exec]})
            tab_chart_series.append({'name': 'Investimento', 'data': [_decimal_to_float(monthly_traffic[mk].get('investimento', 0)) for mk in active_exec]})

    if all_crm_rows:
        groups_exec = _group_rows_by_month(all_crm_rows, 'data_contato')
        month_keys_crm = _last_n_months(12)
        active_crm = [mk for mk in month_keys_crm if mk in groups_exec]
        if active_crm:
            crm_cats = [_short_month_label(y, m) for y, m in active_crm]
            if tab_chart_categories is None:
                tab_chart_categories = crm_cats
            _exec_cs = {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}
            receita_data, conversas_data = [], []
            for mk in active_crm:
                ms = _crm_period_summary(groups_exec[mk], _exec_cs, crm_config)
                receita_data.append(_decimal_to_float(_to_decimal(ms['origem'].get('receita_marketing_pago', Decimal('0')) + ms['origem'].get('receita_marketing_organico', Decimal('0')))))
                conversas_data.append(_decimal_to_float(_to_decimal(ms['geral'].get('conversas', Decimal('0')))))
            tab_chart_series.append({'name': 'Receita Marketing', 'data': receita_data})
            tab_chart_series.append({'name': 'Conversas', 'data': conversas_data})

    tab_chart = {
        'key': 'executive_combined',
        'title': 'Evolução Mensal — Resumo Executivo',
        'categories': tab_chart_categories or [],
        'series': tab_chart_series,
    } if tab_chart_series else None

    summary_panels = [
        _build_summary_panel(
            'presenca_digital',
            'Presença Digital',
            'Soma de presença digital com tráfego pago para leitura consolidada de alcance digital.',
            [
                ('presenca_digital_visualizacoes_totais', 'Visualizações Totais', Decimal(previous_traffic_summary.get('impressoes') or 0) + (previous_social_summary.get('visualizacoes') or Decimal('0')), Decimal(traffic_summary.get('impressoes') or 0) + (social_summary.get('visualizacoes') or Decimal('0')), False, ''),
                ('presenca_digital_alcance_total', 'Alcance Total', Decimal(previous_traffic_summary.get('alcance') or 0) + (previous_social_summary.get('alcance') or Decimal('0')), Decimal(traffic_summary.get('alcance') or 0) + (social_summary.get('alcance') or Decimal('0')), False, ''),
                ('presenca_digital_visualizacoes_redes', 'Visualizações de Redes', previous_social_summary.get('visualizacoes', Decimal('0')), social_summary.get('visualizacoes', Decimal('0')), False, ''),
                ('presenca_digital_impressoes_trafego', 'Impressões de Tráfego', Decimal(previous_traffic_summary.get('impressoes') or 0), Decimal(traffic_summary.get('impressoes') or 0), False, ''),
            ],
        ),
        _build_summary_panel(
            'presenca_fisica',
            'Presença Física',
            'Leads e ações com presença física. Estrutura preparada para evolução.',
            [
                ('presenca_fisica_leads_presenciais', 'Leads com Ação Presencial', Decimal('0'), Decimal('0'), False, ''),
                ('presenca_fisica_oportunidades_presenciais', 'Oportunidades Presenciais', Decimal('0'), Decimal('0'), False, ''),
            ],
        ),
        _build_summary_panel(
            'atendimento',
            'Atendimento',
            'Conversas iniciadas por origem e taxa de conversão do atendimento.',
            [
                ('atendimento_conversas_trafego_pago', 'Conversas Tráfego Pago', previous_crm_summary.get('origem', {}).get('trafego_pago_conversas', Decimal('0')), crm_summary.get('origem', {}).get('trafego_pago_conversas', Decimal('0')), False, ''),
                ('atendimento_conversas_organicas', 'Conversas Orgânicas', previous_crm_summary.get('origem', {}).get('organico_conversas', Decimal('0')), crm_summary.get('origem', {}).get('organico_conversas', Decimal('0')), False, ''),
                ('atendimento_taxa_conversao', 'Taxa de Conversão', previous_crm_summary.get('geral', {}).get('taxa_conversao', Decimal('0')), crm_summary.get('geral', {}).get('taxa_conversao', Decimal('0')), False, '%'),
            ],
        ),
        _build_summary_panel(
            'resultado',
            'Resultado',
            'Vendas e receita separadas entre Marketing e Operação.',
            [
                ('resultado_receita_marketing', 'Receita Marketing', previous_marketing_revenue, marketing_revenue, True, ''),
                ('resultado_receita_operacao', 'Receita Operação', previous_operacao_revenue, operacao_revenue, True, ''),
            ],
        ),
    ]

    return {
        'key': 'analise_completa',
        'panel_type': 'analise_completa',
        'title': 'Resumo Executivo',
        'configured': True,
        'ready': bool(traffic_queryset.exists() or crm_rows or leads_rows or social_rows or crm_config or social_configs or leads_configs),
        'description': 'Painel cruzado geral entre presença digital, atendimento e resultado.',
        'tab_chart': tab_chart,
        'top_cards': [
            {
                'label': 'Receita Marketing Consolidado',
                'value': _format_currency_br(marketing_revenue),
                'tooltip': 'Soma de tráfego pago + venda marketing direta + participação das vendas do operacional.',
            },
            {
                'label': 'Alcance Físico',
                'value': _format_number_br(Decimal('0'), decimals=0),
                'tooltip': 'Indicador reservado para ações presenciais e alcance físico da operação.',
            },
            {
                'label': 'Taxa de Conversão',
                'value': f"{_format_number_br(crm_summary.get('geral', {}).get('taxa_conversao', Decimal('0')), decimals=2)}%",
                'tooltip': 'Conversão geral do CRM no período atual, considerando vendas concluídas sobre conversas.',
            },
            {
                'label': 'Alcance Digital',
                'value': _format_number_br(
                    Decimal(traffic_summary.get('alcance') or 0) + (social_summary.get('alcance') or Decimal('0')),
                    decimals=0,
                ),
                'tooltip': 'Soma do alcance de Tráfego Pago com o alcance dos painéis de Presença Digital.',
            },
        ],
        'summary_panels': summary_panels,
        'competitor_signals': competitor_signals,
    }


def _build_summary_panel(key, title, description, metrics):
    rows = []
    for metric_key, label, previous_value, current_value, currency, suffix in metrics:
        previous_decimal = _to_decimal(previous_value)
        current_decimal = _to_decimal(current_value)
        variation_absolute = current_decimal - previous_decimal
        variation_percent = (variation_absolute / previous_decimal * Decimal('100')) if previous_decimal else None
        rows.append(
            {
                'label': label,
                'current_value': _format_summary_metric(current_decimal, currency, suffix),
                'previous_value': _format_summary_metric(previous_decimal, currency, suffix),
                'period_value': f"{_format_summary_metric(previous_decimal, currency, suffix)} / {_format_summary_metric(current_decimal, currency, suffix)}",
                'variation_value': _format_variation(variation_absolute, variation_percent, metric_key),
                'variation_class': _resolve_crm_variation_class(metric_key, variation_absolute, variation_percent),
            }
        )

    return {
        'key': key,
        'title': title,
        'description': description,
        'rows': rows,
    }


def _calculate_social_marketing_share(social_config, social_summary):
    if not social_config:
        return Decimal('0')
    raw_rate = str((social_config.configuracao_analise_json or {}).get('social_receita_percentual_por_1k_alcance', '')).strip()
    if not raw_rate:
        return Decimal('0')
    try:
        rate_per_1k = Decimal(raw_rate)
    except (InvalidOperation, ValueError):
        return Decimal('0')
    alcance = _to_decimal((social_summary or {}).get('alcance', Decimal('0')))
    share_percent = (alcance / Decimal('1000')) * rate_per_1k if alcance > 0 else Decimal('0')
    share_percent = max(Decimal('0'), min(Decimal('100'), share_percent))
    return share_percent / Decimal('100')


def _calculate_leads_marketing_share(leads_config, leads_summary):
    if not leads_config:
        return Decimal('0')
    raw_rate = str((leads_config.configuracao_analise_json or {}).get('eventos_receita_percentual_por_1k_alcance', '')).strip()
    if not raw_rate:
        return Decimal('0')
    try:
        rate_per_1k = Decimal(raw_rate)
    except (InvalidOperation, ValueError):
        return Decimal('0')
    alcance = _to_decimal((leads_summary or {}).get('participantes_total', Decimal('0')))
    share_percent = (alcance / Decimal('1000')) * rate_per_1k if alcance > 0 else Decimal('0')
    share_percent = max(Decimal('0'), min(Decimal('100'), share_percent))
    return share_percent / Decimal('100')


def _calculate_combined_marketing_share(social_items, leads_items):
    combined_share = Decimal('0')
    for social_config, social_summary in social_items or []:
        combined_share += _calculate_social_marketing_share(social_config, social_summary)
    for leads_config, leads_summary in leads_items or []:
        combined_share += _calculate_leads_marketing_share(leads_config, leads_summary)
    return max(Decimal('0'), min(Decimal('0.4'), combined_share))


def _filter_leads_event_entries(config, period_start=None, period_end=None):
    if not config:
        return []
    rows = []
    for entry in config.eventos_painel.all():
        if period_start and entry.data_evento < period_start:
            continue
        if period_end and entry.data_evento > period_end:
            continue
        rows.append(entry)
    return rows


def _leads_event_period_summary(entries):
    return {
        'eventos_total': len(entries),
        'participantes_total': sum(entry.leads_media for entry in entries),
    }


def _build_social_category_blocks(digital_type, selected_table_keys, selected_chart_keys, current_summary, previous_summary, filter_enabled_map=None):
    filter_enabled_map = filter_enabled_map or {}
    blocks = []
    definitions = _get_social_block_definitions(digital_type)
    for key, title, description, metric_defs, chart_defaults in definitions:
        rows = _social_comparison_rows(metric_defs, current_summary, previous_summary, selected_table_keys)
        if rows:
            blocks.append(
                {
                    'key': key,
                    'title': title,
                    'description': description,
                    'rows': rows,
                    'chart': None,
                    'chart_type': None,
                    'filter_options': [row['label'] for row in rows] if filter_enabled_map.get(key) else [],
                }
            )
    return blocks


def _social_comparison_rows(metric_defs, current_values, previous_values, selected_table_keys):
    rows = []
    for key, label, currency, suffix in metric_defs:
        if key not in selected_table_keys:
            continue
        current_value = current_values.get(key, Decimal('0'))
        previous_value = previous_values.get(key, Decimal('0'))
        variation_absolute = current_value - previous_value
        variation_percent = (variation_absolute / previous_value * Decimal('100')) if previous_value else None
        rows.append(
            {
                'label': label,
                'current_value': _format_social_metric(current_value, currency, suffix),
                'previous_value': _format_social_metric(previous_value, currency, suffix),
                'period_value': f"{_format_social_metric(previous_value, currency, suffix)} / {_format_social_metric(current_value, currency, suffix)}",
                'variation_value': _format_variation(variation_absolute, variation_percent, key),
                'variation_class': _resolve_social_variation_class(key, variation_absolute, variation_percent),
            }
        )
    return rows


def _social_comparison_chart(key, title, metric_defs, current_values, previous_values, selected_chart_keys):
    categories = []
    current_data = []
    previous_data = []
    for metric_key, label, _, _ in metric_defs:
        if metric_key not in selected_chart_keys:
            continue
        categories.append(label)
        current_data.append(_decimal_to_float(current_values.get(metric_key, Decimal('0'))))
        previous_data.append(_decimal_to_float(previous_values.get(metric_key, Decimal('0'))))
    if not categories:
        return None
    return {
        'key': key,
        'title': title,
        'categories': categories,
        'series': [
            {'name': 'Período anterior', 'data': previous_data},
            {'name': 'Período atual', 'data': current_data},
        ],
    }


def _build_crm_category_blocks(selected_table_keys, selected_chart_keys, current_summary, previous_summary, filter_enabled_map=None, all_rows=None, config=None):
    blocks = []
    selected_chart_keys = set(selected_chart_keys or [])
    selected_table_keys = set(selected_table_keys or [])
    filter_enabled_map = filter_enabled_map or {}
    legacy_origin_metric_keys = {'trafego_pago_conversas', 'organico_conversas', 'receita_trafego_pago', 'receita_organico'}

    resultado_metrics = [
        ('receita_total', 'Receita Total', True, ''),
        ('vendas_concluidas', 'Vendas Concluídas', False, ''),
        ('taxa_conversao', 'Taxa de Conversão', False, '%'),
        ('conversas', 'Conversas', False, ''),
        ('ticket_medio', 'Ticket Médio', True, ''),
    ]
    resultado_rows = _crm_comparison_rows(resultado_metrics, current_summary['geral'], previous_summary['geral'], selected_table_keys)
    if resultado_rows:
        blocks.append(
            {
                'key': 'resultado',
                'title': 'Resultado',
                'description': 'Comparativo principal entre os períodos do comercial.',
                'rows': resultado_rows,
                'chart': None,
                'chart_type': None,
                'filter_options': [row['label'] for row in resultado_rows] if filter_enabled_map.get('resultado') else [],
            }
        )

    origem_metrics = [
        ('receita_marketing_pago', 'Marketing Pago', True, ''),
        ('receita_marketing_organico', 'Marketing Orgânico', True, ''),
        ('receita_operacional', 'Operacional', True, ''),
        ('receita_sem_categoria', 'Sem categoria', True, ''),
    ]
    origem_metric_keys = {item[0] for item in origem_metrics}
    if not (origem_metric_keys & selected_table_keys) and (legacy_origin_metric_keys & selected_table_keys):
        selected_table_keys.update(origem_metric_keys)
    if not (origem_metric_keys & selected_chart_keys) and (legacy_origin_metric_keys & selected_chart_keys):
        selected_chart_keys.update(origem_metric_keys)
    origem_rows = _crm_comparison_rows(origem_metrics, current_summary['origem'], previous_summary['origem'], selected_table_keys)
    origem_chart_enabled = bool({key for key in selected_chart_keys if key in origem_metric_keys} or {key for key in selected_table_keys if key in origem_metric_keys})
    if origem_rows:
        blocks.append(
            {
                'key': 'origem',
                'title': 'Origem',
                'description': 'Composição da receita por origem: marketing pago, orgânico, operacional e sem categoria.',
                'rows': origem_rows,
                'chart': None,
                'chart_type': None,
                'filter_options': [row['label'] for row in origem_rows] if filter_enabled_map.get('origem') else [],
            }
        )

    temperatura_rows = _crm_status_comparison_rows(
        current_summary['temperatura_counts'],
        previous_summary['temperatura_counts'],
        'temperatura_lead' in selected_table_keys,
        color_fn=_crm_temperature_color,
    )
    temperatura_chart_enabled = 'temperatura_lead' in selected_chart_keys or ('temperatura_lead' in selected_table_keys and 'temperatura_lead' not in selected_chart_keys)
    temperatura_chart = _crm_distribution_pie_chart(current_summary['temperatura'], 'crm_temperatura', 'Temperatura Leads', _crm_temperature_color) if temperatura_chart_enabled else None
    if temperatura_rows or temperatura_chart:
        blocks.append(
            {
                'key': 'temperatura',
                'title': 'Temperatura Leads',
                'description': 'Distribuição atual em pizza e comparação por tags/temperatura na tabela.',
                'rows': temperatura_rows,
                'chart': temperatura_chart,
                'chart_type': 'pie',
                'filter_options': [row['label'] for row in temperatura_rows] if filter_enabled_map.get('temperatura') else [],
            }
        )

    return blocks


def _crm_comparison_rows(metric_defs, current_values, previous_values, selected_table_keys):
    rows = []
    for key, label, currency, suffix in metric_defs:
        if key not in selected_table_keys:
            continue
        current_value = current_values.get(key, Decimal('0'))
        previous_value = previous_values.get(key, Decimal('0'))
        variation_absolute = current_value - previous_value
        variation_percent = (variation_absolute / previous_value * Decimal('100')) if previous_value else None
        rows.append(
            {
                'label': label,
                'period_value': f"{_format_crm_metric(previous_value, currency, suffix)} / {_format_crm_metric(current_value, currency, suffix)}",
                'previous_value': _format_crm_metric(previous_value, currency, suffix),
                'current_value': _format_crm_metric(current_value, currency, suffix),
                'variation_value': _format_variation(variation_absolute, variation_percent, key),
                'variation_class': _resolve_crm_variation_class(key, variation_absolute, variation_percent),
            }
        )
    return rows


def _crm_comparison_chart(key, title, metric_defs, current_values, previous_values, selected_chart_keys):
    categories = []
    current_data = []
    previous_data = []
    for metric_key, label, _, _ in metric_defs:
        if metric_key not in selected_chart_keys:
            continue
        categories.append(label)
        current_data.append(_decimal_to_float(current_values.get(metric_key, Decimal('0'))))
        previous_data.append(_decimal_to_float(previous_values.get(metric_key, Decimal('0'))))
    if not categories:
        return None
    return {
        'key': key,
        'title': title,
        'categories': categories,
        'series': [
            {'name': 'Período anterior', 'data': previous_data},
            {'name': 'Período atual', 'data': current_data},
        ],
    }


def _crm_status_comparison_rows(current_status_counts, previous_status_counts, include_table, color_fn=None):
    if not include_table:
        return []
    status_labels = sorted(set(current_status_counts.keys()) | set(previous_status_counts.keys()))
    rows = []
    for label in status_labels:
        current_value = Decimal(current_status_counts.get(label, 0))
        previous_value = Decimal(previous_status_counts.get(label, 0))
        variation_absolute = current_value - previous_value
        variation_percent = (variation_absolute / previous_value * Decimal('100')) if previous_value else None
        rows.append(
            {
                'label': label,
                'label_color': color_fn(label) if color_fn else _crm_status_color(label),
                'period_value': f'{_format_number_br(previous_value, decimals=0)} / {_format_number_br(current_value, decimals=0)}',
                'previous_value': _format_number_br(previous_value, decimals=0),
                'current_value': _format_number_br(current_value, decimals=0),
                'variation_value': _format_variation(variation_absolute, variation_percent, 'conversas'),
                'variation_class': _resolve_crm_variation_class('conversas', variation_absolute, variation_percent),
            }
        )
    return rows


def _crm_distribution_pie_chart(current_distribution, key, title, color_fn):
    if not current_distribution:
        return None
    labels = list(current_distribution.keys())
    data = [_decimal_to_float(current_distribution[label]) for label in labels]
    return {
        'key': key,
        'title': title,
        'labels': labels,
        'series': data,
        'colors': [color_fn(label) for label in labels],
    }


def _crm_status_pie_chart(current_status):
    return _crm_distribution_pie_chart(current_status, 'crm_status', 'Status', _crm_status_color)


def _build_origem_stacked_area_chart(all_rows, config):
    """Build mixed chart: Receita Total as line + stacked area by origem category."""
    if not all_rows:
        return None
    closed_status = {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}
    groups = _group_rows_by_month(all_rows, 'data_contato')
    month_keys = _last_n_months(12)
    active = [mk for mk in month_keys if mk in groups]
    if not active:
        return None
    categories = [_short_month_label(y, m) for y, m in active]
    origem_defs = [
        ('receita_marketing_pago', 'Marketing Pago', '#175cd3'),
        ('receita_marketing_organico', 'Marketing Orgânico', '#2d6a4f'),
        ('receita_operacional', 'Operacional', '#c67a1a'),
        ('receita_sem_categoria', 'Sem categoria', '#94a3b8'),
    ]
    # Pre-compute summaries once per month
    monthly_summaries = {mk: _crm_period_summary(groups[mk], closed_status, config) for mk in active}
    # Receita Total as line series
    total_data = [
        _decimal_to_float(_to_decimal(monthly_summaries[mk]['geral'].get('receita_total', Decimal('0'))))
        for mk in active
    ]
    series = [{'name': 'Receita Total', 'type': 'line', 'data': total_data}]
    colors = ['#0f172a']
    # Origem breakdown as stacked area series
    for field_key, label, color in origem_defs:
        data = [
            _decimal_to_float(_to_decimal(monthly_summaries[mk]['origem'].get(field_key, Decimal('0'))))
            for mk in active
        ]
        if any(v > 0 for v in data):
            series.append({'name': label, 'type': 'area', 'data': data})
            colors.append(color)
    if len(series) == 1:
        return None
    return {
        'key': 'crm_origem_stacked',
        'title': 'Evolução Mensal — Resultado por Origem',
        'categories': categories,
        'series': series,
        'colors': colors,
        'chart_type': 'mixed_area',
    }


def _format_crm_metric(value, currency=False, suffix=''):
    if currency:
        return _format_currency_br(value)
    if suffix == '%':
        return f'{_format_number_br(value, decimals=2)}%'
    return _format_number_br(value)


def _format_social_metric(value, currency=False, suffix=''):
    if currency:
        return _format_currency_br(value)
    if suffix == '%':
        return f'{_format_number_br(value, decimals=2)}%'
    return _format_number_br(value)


def _crm_status_color(label):
    normalized = _normalize_status_label(label)
    if normalized in CRM_STATUS_COLOR_MAP:
        return CRM_STATUS_COLOR_MAP[normalized]
    for term, color in CRM_STATUS_COLOR_RULES:
        if term in normalized:
            return color
    return '#175cd3'


def _crm_origin_color(label):
    normalized = _normalize_status_label(label)
    if 'marketing pago' in normalized:
        return '#175cd3'
    if 'marketing organico' in normalized:
        return '#2d6a4f'
    if 'operacional' in normalized:
        return '#c67a1a'
    if 'sem categoria' in normalized:
        return '#94a3b8'
    return '#175cd3'


def _crm_temperature_color(label):
    normalized = _normalize_status_label(label)
    for term, color in LEAD_TEMPERATURE_COLOR_RULES:
        if term in normalized:
            return color
    return '#175cd3'


def _normalize_lead_temperature_label(value):
    raw_text = str(value or '').strip()
    if not raw_text:
        return 'Não informado'
    text = unicodedata.normalize('NFKD', raw_text).encode('ascii', 'ignore').decode('ascii').lower()
    parts = [part.strip() for part in re.split(r'[,;|/]+', text) if part.strip()]
    normalized_parts = parts or [text.strip()]
    if any('cliente' in part for part in normalized_parts):
        return 'Cliente'
    if any('muito quente' in part for part in normalized_parts):
        return 'Muito Quente'
    if any('quente' in part for part in normalized_parts):
        return 'Quente'
    if any('frio' in part for part in normalized_parts):
        return 'Frio'
    return 'Não informado'


def _sort_temperature_counts(counts):
    ordered = {}
    for label in LEAD_TEMPERATURE_DISPLAY_ORDER:
        if label in counts:
            ordered[label] = counts[label]
    for label, value in counts.items():
        if label not in ordered:
            ordered[label] = value
    return ordered


def _empty_tab(key, title):
    return {
        'key': key,
        'panel_type': key,
        'title': title,
        'configured': False,
        'ready': False,
        'config_name': '',
        'description': '',
    }


def _read_mapped_rows(config, period_start=None, period_end=None, date_key=''):
    if not config or not config.mapeamento_json:
        return []
    rows = []
    uploads = _get_panel_uploads(config)
    for upload in uploads:
        dataframe = read_uploaded_dataframe(upload.arquivo.path, upload.nome_arquivo or upload.arquivo.name)
        for _, source_row in dataframe.iterrows():
            row = {}
            for field_key, column_name in (config.mapeamento_json or {}).items():
                row[field_key] = _serialize_value(source_row.get(column_name, ''))
            rows.append(row)
    return rows


def _read_social_rows(config, period_start=None, period_end=None):
    if not config or not config.mapeamento_json:
        return []
    deduped_rows = {}
    digital_type = str((config.configuracao_analise_json or {}).get('digital_type', 'instagram')).strip()
    uploads = _get_panel_uploads(config)
    for upload in uploads:
        upload_type = getattr(upload, 'tipo_upload', '') or ('principal' if digital_type != 'instagram' else _normalize_social_content_type('', '', upload.nome_arquivo))
        social_mapping = (config.mapeamento_json or {}).get(upload_type, {}) or (config.mapeamento_json or {}).get('principal', {})
        if not social_mapping:
            continue
        dataframe = read_uploaded_dataframe(upload.arquivo.path, upload.nome_arquivo or upload.arquivo.name)
        for _, source_row in dataframe.iterrows():
            row = {}
            for field_key, column_name in social_mapping.items():
                row[field_key] = _serialize_value(source_row.get(column_name, ''))
            row['tipo_conteudo_normalizado'] = _normalize_social_content_type(
                row.get('tipo_conteudo', ''),
                getattr(upload, 'tipo_upload', ''),
                upload.nome_arquivo,
            )
            dedupe_key = str(row.get('id_publicacao', '')).strip() or f"{upload.pk}:{source_row.name}"
            deduped_rows[dedupe_key] = row
    rows = list(deduped_rows.values())
    rows.sort(key=lambda item: _parse_date(item.get('data_publicacao')) or pd.Timestamp.min.date(), reverse=True)
    return rows


def _serialize_value(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    if hasattr(value, 'isoformat'):
        try:
            return value.isoformat()
        except TypeError:
            return str(value)
    return str(value).strip()


def _parse_date(value):
    if not value:
        return None
    text = str(value).strip()
    us_datetime_patterns = (
        '%m/%d/%Y %H:%M',
        '%m/%d/%Y %H:%M:%S',
        '%m/%d/%Y',
    )
    if '/' in text:
        for pattern in us_datetime_patterns:
            parsed = pd.to_datetime(text, format=pattern, errors='coerce')
            if not pd.isna(parsed):
                return parsed.date()
    if re.match(r'^\d{4}-\d{2}-\d{2}', text):
        parsed = pd.to_datetime(text, errors='coerce')
    else:
        parsed = pd.to_datetime(text, errors='coerce', dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.date()


def _filter_rows_by_period(rows, period_start, period_end, date_key):
    if not rows:
        return []
    if not (period_start and period_end and date_key):
        return list(rows)
    filtered = []
    for row in rows:
        row_date = _parse_date(row.get(date_key))
        if row_date is None or period_start <= row_date <= period_end:
            filtered.append(row)
    return filtered


def _get_panel_uploads(config):
    prefetched = getattr(config, '_prefetched_objects_cache', {}).get('uploads_painel')
    if prefetched is not None:
        return list(prefetched)
    return list(UploadPainel.objects.filter(configuracao=config).order_by('-criado_em', '-pk'))


def _to_decimal(value):
    if value in (None, ''):
        return Decimal('0')
    text = str(value).strip().replace('R$', '').replace('%', '').replace(' ', '')
    if ',' in text and '.' in text:
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '').replace(',', '.')
        else:
            text = text.replace(',', '')
    elif ',' in text:
        text = text.replace('.', '').replace(',', '.')
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal('0')


def _decimal_to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


_MESES_PT_SHORT = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez',
}


def _short_month_label(year, month):
    return f"{_MESES_PT_SHORT[month]}/{str(year)[2:]}"


def _last_n_months(n=12):
    """Returns list of (year, month) tuples for last n months, oldest first."""
    from datetime import date as _date
    today = _date.today()
    months = []
    for i in range(n - 1, -1, -1):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))
    return months


def _group_rows_by_month(rows, date_key):
    """Groups rows into a dict {(year, month): [rows]} based on a date field."""
    from collections import defaultdict
    groups = defaultdict(list)
    for row in rows:
        d = _parse_date(row.get(date_key))
        if d:
            groups[(d.year, d.month)].append(row)
    return groups


def _build_monthly_traffic_data(empresa):
    """Queries CampanhaMetric for empresa grouped by month. Returns {(year, month): metric_dict}."""
    from .models import CampanhaMetric
    from django.db.models.functions import TruncMonth
    from django.db.models import Sum as OrmSum
    monthly_qs = (
        CampanhaMetric.objects
        .filter(upload__empresa=empresa)
        .annotate(mes=TruncMonth('data'))
        .values('mes')
        .annotate(
            s_investimento=OrmSum('investimento'),
            s_impressoes=OrmSum('impressoes'),
            s_alcance=OrmSum('alcance'),
            s_cliques=OrmSum('cliques'),
            s_resultados=OrmSum('resultados'),
        )
        .order_by('mes')
    )
    result = {}
    for row in monthly_qs:
        if not row['mes']:
            continue
        key = (row['mes'].year, row['mes'].month)
        inv = Decimal(row['s_investimento'] or 0)
        imp = int(row['s_impressoes'] or 0)
        alc = int(row['s_alcance'] or 0)
        cli = int(row['s_cliques'] or 0)
        res = Decimal(row['s_resultados'] or 0)
        ctr = (Decimal(cli) / Decimal(imp) * Decimal('100')) if imp else Decimal('0')
        cpc = (inv / Decimal(cli)) if cli else Decimal('0')
        cpm = (inv / Decimal(imp) * Decimal('1000')) if imp else Decimal('0')
        cpl = (inv / res) if res else Decimal('0')
        freq = (Decimal(imp) / Decimal(alc)) if alc else Decimal('0')
        taxa_conv = (res / Decimal(cli) * Decimal('100')) if cli else Decimal('0')
        result[key] = {
            'investimento': inv,
            'impressoes': Decimal(imp),
            'alcance': Decimal(alc),
            'resultado_principal': res,
            'ctr': ctr,
            'cpc': cpc,
            'cpm': cpm,
            'cpl': cpl,
            'frequencia': freq,
            'taxa_conversao': taxa_conv,
            'score_relevancia': _calculate_relevance_score(ctr, cpc, cpm, freq, taxa_conv),
        }
    return result


def _build_traffic_line_chart(empresa, block_key, chart_metric_keys, metric_definitions):
    """Build line chart showing monthly evolution for traffic metrics."""
    if not empresa or not chart_metric_keys:
        return None
    monthly_data = _build_monthly_traffic_data(empresa)
    month_keys = _last_n_months(12)
    active_months = [mk for mk in month_keys if mk in monthly_data]
    if not active_months:
        return None
    categories = [_short_month_label(y, m) for y, m in active_months]
    series = []
    for metric_key in chart_metric_keys:
        if metric_key not in metric_definitions:
            continue
        label = metric_definitions[metric_key]['label']
        data = [_decimal_to_float(_to_decimal(monthly_data[mk].get(metric_key, 0))) for mk in active_months]
        series.append({'name': label, 'data': data})
    if not series:
        return None
    return {
        'key': block_key,
        'title': 'Evolução Mensal',
        'categories': categories,
        'series': series,
    }


def _build_crm_monthly_line_chart(all_rows, config, chart_key, metric_defs, selected_chart_keys):
    """Build line chart showing monthly evolution of CRM metrics."""
    if not all_rows:
        return None
    closed_status = {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}
    groups = _group_rows_by_month(all_rows, 'data_contato')
    month_keys = _last_n_months(12)
    active_months = [mk for mk in month_keys if mk in groups]
    if not active_months:
        return None
    categories = [_short_month_label(y, m) for y, m in active_months]
    metric_key_set = {item[0] for item in metric_defs}
    keys_to_chart = [key for key in selected_chart_keys if key in metric_key_set]
    if not keys_to_chart:
        keys_to_chart = [item[0] for item in metric_defs if item[0] in metric_key_set][:3]
    label_map = {item[0]: item[1] for item in metric_defs}
    series = []
    for metric_key in keys_to_chart:
        monthly_values = []
        for mk in active_months:
            monthly_summary = _crm_period_summary(groups[mk], closed_status, config)
            val = _decimal_to_float(_to_decimal(monthly_summary['geral'].get(metric_key, 0)))
            monthly_values.append(val)
        series.append({'name': label_map.get(metric_key, metric_key), 'data': monthly_values})
    if not series:
        return None
    return {
        'key': chart_key,
        'title': 'Evolução Mensal',
        'categories': categories,
        'series': series,
    }


def _build_social_monthly_line_chart(all_rows, digital_type, chart_key, metric_defs, selected_chart_keys):
    """Build line chart showing monthly evolution of social metrics."""
    if not all_rows:
        return None
    groups = _group_rows_by_month(all_rows, 'data_publicacao')
    month_keys = _last_n_months(12)
    active_months = [mk for mk in month_keys if mk in groups]
    if not active_months:
        return None
    categories = [_short_month_label(y, m) for y, m in active_months]
    metric_key_set = {item[0] for item in metric_defs}
    keys_to_chart = [key for key in selected_chart_keys if key in metric_key_set]
    if not keys_to_chart:
        keys_to_chart = [item[0] for item in metric_defs if item[0] in metric_key_set][:2]
    label_map = {item[0]: item[1] for item in metric_defs}
    series = []
    for metric_key in keys_to_chart:
        monthly_values = []
        for mk in active_months:
            summary = _social_period_summary(groups[mk], digital_type=digital_type)
            val = _decimal_to_float(_to_decimal(summary.get(metric_key, 0)))
            monthly_values.append(val)
        series.append({'name': label_map.get(metric_key, metric_key), 'data': monthly_values})
    if not series:
        return None
    return {
        'key': chart_key,
        'title': 'Evolução Mensal',
        'categories': categories,
        'series': series,
    }


def _build_leads_monthly_line_chart(config, key='leads_mensal'):
    """Build line chart showing monthly evolution of leads/event participants."""
    from collections import defaultdict
    groups = defaultdict(int)
    for entry in config.eventos_painel.all():
        mk = (entry.data_evento.year, entry.data_evento.month)
        groups[mk] += entry.leads_media
    month_keys = _last_n_months(12)
    active_months = [mk for mk in month_keys if mk in groups]
    if not active_months:
        return None
    categories = [_short_month_label(y, m) for y, m in active_months]
    data = [float(groups[mk]) for mk in active_months]
    return {
        'key': key,
        'title': 'Evolução Mensal',
        'categories': categories,
        'series': [{'name': 'Pessoas alcançadas', 'data': data}],
    }


def _top_values(rows, key):
    counts = {}
    for row in rows:
        value = str(row.get(key, '')).strip()
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]


def _crm_period_summary(rows, closed_status, config):
    conversations = Decimal(len(rows))
    vendas_concluidas = Decimal(sum(1 for row in rows if _crm_is_closed_sale(row, closed_status)))
    receita_total = sum((_to_decimal(row.get('valor_venda')) for row in rows), Decimal('0'))
    ticket_medio = (receita_total / vendas_concluidas) if vendas_concluidas else Decimal('0')
    taxa_conversao = (vendas_concluidas / conversations * Decimal('100')) if conversations else Decimal('0')

    marketing_pago_rows = [row for row in rows if _crm_is_paid_row(row, config)]
    marketing_organico_rows = [row for row in rows if _crm_is_marketing_organico_row(row, config)]
    operacao_rows = [row for row in rows if _crm_is_operacional_row(row)]
    sem_categoria_rows = [
        row for row in rows
        if not _crm_is_paid_row(row, config)
        and not _crm_is_marketing_organico_row(row, config)
        and not _crm_is_operacional_row(row)
    ]
    origem = {
        'trafego_pago_conversas': Decimal(len(marketing_pago_rows)),
        'organico_conversas': Decimal(len(rows) - len(marketing_pago_rows)),
        'receita_marketing_pago': sum((_to_decimal(row.get('valor_venda')) for row in marketing_pago_rows), Decimal('0')),
        'receita_marketing_organico': sum((_to_decimal(row.get('valor_venda')) for row in marketing_organico_rows), Decimal('0')),
        'receita_operacional': sum((_to_decimal(row.get('valor_venda')) for row in operacao_rows), Decimal('0')),
        'receita_sem_categoria': sum((_to_decimal(row.get('valor_venda')) for row in sem_categoria_rows), Decimal('0')),
    }

    status_counts = {}
    for row in rows:
        label = str(row.get('status_fechamento', '')).strip() or 'Não informado'
        status_counts[label] = status_counts.get(label, 0) + 1
    status = {}
    total_status = sum(status_counts.values())
    for label, count in status_counts.items():
        status[label] = (Decimal(count) / Decimal(total_status) * Decimal('100')) if total_status else Decimal('0')

    temperatura_counts = {}
    for row in rows:
        label = _normalize_lead_temperature_label(row.get('tag_lead', ''))
        temperatura_counts[label] = temperatura_counts.get(label, 0) + 1
    temperatura_counts = _sort_temperature_counts(temperatura_counts)
    temperatura = {}
    total_temperatura = sum(temperatura_counts.values())
    for label, count in temperatura_counts.items():
        temperatura[label] = (Decimal(count) / Decimal(total_temperatura) * Decimal('100')) if total_temperatura else Decimal('0')

    return {
        'geral': {
            'receita_total': receita_total,
            'vendas_concluidas': vendas_concluidas,
            'taxa_conversao': taxa_conversao,
            'conversas': conversations,
            'ticket_medio': ticket_medio,
        },
        'origem': origem,
        'status': status,
        'status_counts': status_counts,
        'temperatura': temperatura,
        'temperatura_counts': temperatura_counts,
    }


def _get_social_digital_type(config):
    if not config:
        return 'instagram'
    return str((config.configuracao_analise_json or {}).get('digital_type', 'instagram')).strip() or 'instagram'


def _social_tab_description(digital_type):
    descriptions = {
        'instagram': 'Comparativo do desempenho orgânico do Instagram entre período atual e anterior, baseado apenas em uploads reais.',
        'facebook': 'Comparativo do desempenho orgânico do Facebook entre período atual e anterior, baseado apenas em uploads reais.',
        'tiktok': 'Comparativo do desempenho orgânico do TikTok entre período atual e anterior, baseado apenas em uploads reais.',
        'x': 'Comparativo do desempenho orgânico do X / Twitter entre período atual e anterior, baseado apenas em uploads reais.',
        'website': 'Comparativo de tráfego e conversão do website com base nos uploads reais do Google Analytics.',
        'outro': 'Comparativo do desempenho do canal digital entre período atual e anterior, baseado apenas em uploads reais.',
    }
    return descriptions.get(digital_type, descriptions['outro'])


def _get_social_block_definitions(digital_type):
    if digital_type == 'website':
        return [
            (
                'visao_geral',
                'Visão Geral',
                'Leitura consolidada do tráfego do website no período.',
                [
                    ('usuarios', 'Usuários', False, ''),
                    ('sessoes', 'Sessões', False, ''),
                    ('visualizacoes_pagina', 'Visualizações de Página', False, ''),
                ],
                ['usuarios', 'sessoes', 'visualizacoes_pagina'],
            ),
            (
                'aquisicao',
                'Aquisição',
                'Indicadores de aquisição e qualidade de sessão.',
                [
                    ('novos_usuarios', 'Novos Usuários', False, ''),
                    ('sessoes_engajadas', 'Sessões Engajadas', False, ''),
                    ('taxa_engajamento', 'Taxa de Engajamento', False, '%'),
                ],
                ['novos_usuarios', 'sessoes_engajadas', 'taxa_engajamento'],
            ),
            (
                'conversao',
                'Conversão',
                'Indicadores de resultado do website.',
                [
                    ('conversoes', 'Conversões', False, ''),
                ],
                ['conversoes'],
            ),
        ]
    if digital_type == 'instagram':
        return [
            (
                'visao_geral',
                'Visão Geral',
                'Bloco principal consolidado do desempenho social.',
                [
                    ('quantidade_publicacoes', 'Quantidade de Publicações', False, ''),
                    ('visualizacoes', 'Visualizações', False, ''),
                    ('alcance', 'Alcance', False, ''),
                    ('curtidas', 'Curtidas', False, ''),
                    ('compartilhamentos', 'Compartilhamentos', False, ''),
                ],
                ['quantidade_publicacoes', 'visualizacoes', 'alcance'],
            ),
            (
                'posts',
                'Posts',
                'Desempenho consolidado apenas dos conteúdos do tipo post.',
                [
                    ('quantidade_posts', 'Quantidade de Posts', False, ''),
                    ('visualizacoes_posts', 'Visualizações dos Posts', False, ''),
                    ('alcance_posts', 'Alcance dos Posts', False, ''),
                    ('curtidas_posts', 'Curtidas dos Posts', False, ''),
                    ('compartilhamentos_posts', 'Compartilhamentos dos Posts', False, ''),
                ],
                ['quantidade_posts', 'visualizacoes_posts', 'alcance_posts'],
            ),
            (
                'stories',
                'Stories',
                'Desempenho consolidado apenas dos conteúdos do tipo story.',
                [
                    ('quantidade_stories', 'Quantidade de Stories', False, ''),
                    ('visualizacoes_stories', 'Visualizações dos Stories', False, ''),
                    ('alcance_stories', 'Alcance dos Stories', False, ''),
                    ('curtidas_stories', 'Curtidas dos Stories', False, ''),
                    ('compartilhamentos_stories', 'Compartilhamentos dos Stories', False, ''),
                ],
                ['quantidade_stories', 'visualizacoes_stories', 'alcance_stories'],
            ),
            (
                'engajamento',
                'Engajamento',
                'Indicadores complementares de interação.',
                [
                    ('curtidas', 'Curtidas', False, ''),
                    ('compartilhamentos', 'Compartilhamentos', False, ''),
                    ('comentarios', 'Comentários', False, ''),
                    ('salvamentos', 'Salvamentos', False, ''),
                    ('respostas', 'Respostas', False, ''),
                    ('cliques_link', 'Cliques no Link', False, ''),
                    ('visitas_perfil', 'Visitas ao Perfil', False, ''),
                ],
                ['curtidas', 'compartilhamentos', 'comentarios'],
            ),
        ]
    if digital_type == 'tiktok':
        return [
            (
                'visao_geral',
                'Visão Geral',
                'Desempenho consolidado do conteúdo publicado no TikTok.',
                [
                    ('quantidade_publicacoes', 'Quantidade de Conteúdos', False, ''),
                    ('visualizacoes', 'Visualizações', False, ''),
                    ('alcance', 'Alcance', False, ''),
                ],
                ['quantidade_publicacoes', 'visualizacoes', 'alcance'],
            ),
            (
                'engajamento',
                'Engajamento',
                'Interações do conteúdo com a audiência.',
                [
                    ('curtidas', 'Curtidas', False, ''),
                    ('compartilhamentos', 'Compartilhamentos', False, ''),
                    ('comentarios', 'Comentários', False, ''),
                    ('salvamentos', 'Salvamentos', False, ''),
                ],
                ['curtidas', 'compartilhamentos', 'comentarios'],
            ),
            (
                'audiencia',
                'Audiência',
                'Sinais de interesse pela conta e crescimento.',
                [
                    ('visitas_perfil', 'Visitas ao Perfil', False, ''),
                    ('seguimentos', 'Seguimentos', False, ''),
                ],
                ['visitas_perfil', 'seguimentos'],
            ),
        ]
    if digital_type == 'x':
        return [
            (
                'visao_geral',
                'Visão Geral',
                'Desempenho consolidado do conteúdo publicado no X.',
                [
                    ('quantidade_publicacoes', 'Quantidade de Posts', False, ''),
                    ('visualizacoes', 'Impressões', False, ''),
                    ('alcance', 'Alcance', False, ''),
                ],
                ['quantidade_publicacoes', 'visualizacoes', 'alcance'],
            ),
            (
                'interacao',
                'Interação',
                'Respostas e compartilhamentos do conteúdo.',
                [
                    ('curtidas', 'Curtidas', False, ''),
                    ('compartilhamentos', 'Reposts / Compartilhamentos', False, ''),
                    ('comentarios', 'Respostas', False, ''),
                ],
                ['curtidas', 'compartilhamentos', 'comentarios'],
            ),
            (
                'trafego',
                'Tráfego',
                'Sinais de tráfego gerado e interesse no perfil.',
                [
                    ('cliques_link', 'Cliques no Link', False, ''),
                    ('visitas_perfil', 'Visitas ao Perfil', False, ''),
                    ('seguimentos', 'Seguimentos', False, ''),
                ],
                ['cliques_link', 'visitas_perfil', 'seguimentos'],
            ),
        ]
    return [
        (
            'visao_geral',
            'Visão Geral',
            'Desempenho consolidado do canal digital no período.',
            [
                ('quantidade_publicacoes', 'Quantidade de Conteúdos', False, ''),
                ('visualizacoes', 'Visualizações', False, ''),
                ('alcance', 'Alcance', False, ''),
            ],
            ['quantidade_publicacoes', 'visualizacoes', 'alcance'],
        ),
        (
            'engajamento',
            'Engajamento',
            'Interações principais do conteúdo.',
            [
                ('curtidas', 'Curtidas', False, ''),
                ('compartilhamentos', 'Compartilhamentos', False, ''),
                ('comentarios', 'Comentários', False, ''),
            ],
            ['curtidas', 'compartilhamentos', 'comentarios'],
        ),
        (
            'audiencia',
            'Audiência',
            'Sinais de tráfego e crescimento do canal.',
            [
                ('cliques_link', 'Cliques no Link', False, ''),
                ('visitas_perfil', 'Visitas ao Perfil', False, ''),
                ('seguimentos', 'Seguimentos', False, ''),
            ],
            ['cliques_link', 'visitas_perfil', 'seguimentos'],
        ),
    ]


def _aggregate_social_summaries(summaries):
    aggregate = {'visualizacoes': Decimal('0'), 'alcance': Decimal('0')}
    for summary in summaries or []:
        aggregate['visualizacoes'] += _to_decimal((summary or {}).get('visualizacoes', Decimal('0')))
        aggregate['alcance'] += _to_decimal((summary or {}).get('alcance', Decimal('0')))
    return aggregate


def _social_period_summary(rows, digital_type='instagram'):
    def sum_key(dataset, field):
        return sum((_to_decimal(item.get(field)) for item in dataset), Decimal('0'))

    if digital_type == 'website':
        usuarios = sum_key(rows, 'usuarios')
        visualizacoes_pagina = sum_key(rows, 'visualizacoes_pagina')
        sessoes = sum_key(rows, 'sessoes')
        sessoes_engajadas = sum_key(rows, 'sessoes_engajadas')
        taxa_engajamento = (sessoes_engajadas / sessoes * Decimal('100')) if sessoes else Decimal('0')
        return {
            'usuarios': usuarios,
            'novos_usuarios': sum_key(rows, 'novos_usuarios'),
            'sessoes': sessoes,
            'sessoes_engajadas': sessoes_engajadas,
            'visualizacoes_pagina': visualizacoes_pagina,
            'taxa_engajamento': taxa_engajamento,
            'conversoes': sum_key(rows, 'conversoes'),
            'visualizacoes': visualizacoes_pagina,
            'alcance': usuarios,
        }

    posts = [row for row in rows if row.get('tipo_conteudo_normalizado') == 'post']
    stories = [row for row in rows if row.get('tipo_conteudo_normalizado') == 'story']
    summary = {
        'quantidade_publicacoes': Decimal(len(rows)),
        'visualizacoes': sum_key(rows, 'visualizacoes'),
        'alcance': sum_key(rows, 'alcance'),
        'curtidas': sum_key(rows, 'curtidas'),
        'compartilhamentos': sum_key(rows, 'compartilhamentos'),
        'quantidade_posts': Decimal(len(posts)),
        'visualizacoes_posts': sum_key(posts, 'visualizacoes'),
        'alcance_posts': sum_key(posts, 'alcance'),
        'curtidas_posts': sum_key(posts, 'curtidas'),
        'compartilhamentos_posts': sum_key(posts, 'compartilhamentos'),
        'quantidade_stories': Decimal(len(stories)),
        'visualizacoes_stories': sum_key(stories, 'visualizacoes'),
        'alcance_stories': sum_key(stories, 'alcance'),
        'curtidas_stories': sum_key(stories, 'curtidas'),
        'compartilhamentos_stories': sum_key(stories, 'compartilhamentos'),
        'comentarios': sum_key(rows, 'comentarios'),
        'salvamentos': sum_key(rows, 'salvamentos'),
        'respostas': sum_key(rows, 'respostas'),
        'cliques_link': sum_key(rows, 'cliques_link'),
        'visitas_perfil': sum_key(rows, 'visitas_perfil'),
        'seguimentos': sum_key(rows, 'seguimentos'),
    }
    return summary


def _crm_is_paid_row(row, config):
    url = str(row.get('ads_parametros_url', '')).strip().lower()
    contains_value = str((config.configuracao_analise_json or {}).get('crm_origem_paga_contem', '')).strip().lower()
    return (url.startswith('https://www.') if url else False) or (contains_value and contains_value in url)


def _crm_is_marketing_organico_row(row, config):
    if _crm_is_paid_row(row, config):
        return False
    origem = _normalize_status_label(row.get('origem_lead', ''))
    return any(term in origem for term in ('marketing', 'google'))


def _crm_is_operacional_row(row):
    origem = _normalize_status_label(row.get('origem_lead', ''))
    return any(term in origem for term in ('cliente base', 'indicacao'))


def _normalize_social_content_type(value, upload_type='', file_name=''):
    normalized = _normalize_status_label(value)
    file_hint = _normalize_status_label(file_name)
    upload_hint = _normalize_status_label(upload_type)
    if any(term in normalized for term in ('story', 'stories', 'storie')):
        return 'story'
    if any(term in normalized for term in ('post', 'feed', 'photo', 'foto', 'carousel', 'carrossel')):
        return 'post'
    if 'stories' in upload_hint or 'story' in upload_hint or 'stories' in file_hint or 'story' in file_hint:
        return 'story'
    return 'post'


def _crm_is_closed_sale(row, closed_status):
    status_text = _normalize_status_label(row.get('status_fechamento', ''))
    revenue = _to_decimal(row.get('valor_venda'))
    if revenue > 0:
        return True
    if status_text in closed_status:
        return True
    return any(term in status_text for term in ('venda concluida', 'venda concluída', 'fechado', 'ganho', 'vendido'))


def _normalize_status_label(value):
    text = str(value or '').strip().lower()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'^\s*\d+\s*-\s*', '', text)
    return text.strip()




def _sum_values(rows, group_key, value_key):
    grouped = {}
    for row in rows:
        label = str(row.get(group_key, '')).strip() or 'Não informado'
        grouped[label] = grouped.get(label, Decimal('0')) + _to_decimal(row.get(value_key))
    return sorted(grouped.items(), key=lambda item: (-item[1], item[0]))[:8]


def _crm_status_percent(rows):
    counts = {}
    total = 0
    for row in rows:
        label = str(row.get('status_fechamento', '')).strip() or 'Não informado'
        counts[label] = counts.get(label, 0) + 1
        total += 1
    if not total:
        return []
    return sorted(
        [(label, Decimal(count) / Decimal(total) * Decimal('100')) for label, count in counts.items()],
        key=lambda item: (-item[1], item[0]),
    )[:8]


def _crm_gap_vendas(rows, closed_status):
    status_sales = sum(1 for row in rows if str(row.get('status_fechamento', '')).strip().lower() in closed_status)
    filled_sales = sum(1 for row in rows if _to_decimal(row.get('valor_venda')) > 0)
    return {
        'status_sales': status_sales,
        'filled_sales': filled_sales,
        'gap': abs(status_sales - filled_sales),
    }


def _crm_source_breakdown(rows, config):
    contains_value = str((config.configuracao_analise_json or {}).get('crm_origem_paga_contem', '')).strip().lower()
    paid = 0
    organic = 0
    for row in rows:
        url = str(row.get('ads_parametros_url', '')).strip().lower()
        is_paid = False
        if url.startswith('https://www.'):
            is_paid = True
        if contains_value and contains_value in url:
            is_paid = True
        if is_paid:
            paid += 1
        else:
            organic += 1
    return {'paid': paid, 'organic': organic}


def _is_paid_traffic_sale(row):
    haystack = ' '.join(
        [
            str(row.get('origem_lead', '')),
            str(row.get('canal', '')),
            str(row.get('tag_lead', '')),
        ]
    ).lower()
    return any(term in haystack for term in PAID_TRAFFIC_HINTS)


def _is_marketing_sale(row, config):
    origem = _normalize_status_label(row.get('origem_lead', ''))
    if any(term in origem for term in ('marketing', 'google')):
        return True
    return _crm_is_paid_row(row, config) if config else _is_paid_traffic_sale(row)


def _is_cliente_base_sale(row):
    origem = _normalize_status_label(row.get('origem_lead', ''))
    return 'cliente base' in origem


def _is_operacao_sale(row):
    origem = _normalize_status_label(row.get('origem_lead', ''))
    return any(term in origem for term in ('cliente base', 'indicacao', 'indicação'))


def _is_sem_categoria_sale(row, config):
    return (
        not _is_marketing_sale(row, config)
        and not _is_operacao_sale(row)
    )


def _is_operacao_or_sem_categoria_sale(row, config):
    return _is_operacao_sale(row) or _is_sem_categoria_sale(row, config)


def _build_competitor_signals(empresa):
    if not empresa:
        return []
    profiles = competitor_profiles(ConcorrenteAd.objects.filter(empresa=empresa))
    signals = []
    for item in profiles[:5]:
        signals.append(
            {
                'nome': item['nome'],
                'atividade': item['activity_label'],
                'ads_count': item['real_ads_count'],
                'cadencia': item.get('feed_cadencia') or 'Sem leitura de cadência',
            }
        )
    return signals


def _build_metric_cards(kpis, selected_keys, formatters):
    keys = selected_keys or list(formatters.keys())
    cards = []
    for key in keys:
        if key not in formatters:
            continue
        label, formatter = formatters[key]
        cards.append({'label': label, 'value': formatter(kpis.get(key, 0))})
    return cards


def _build_traffic_metric_definitions(result_label):
    return {
        'investimento': {'label': 'Investimento Total', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['investimento'], 'formatter': lambda value: _format_currency_br(value)},
        'cpm': {'label': 'CPM', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['cpm'], 'formatter': lambda value: _format_currency_br(value)},
        'cpc': {'label': 'CPC', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['cpc'], 'formatter': lambda value: _format_currency_br(value)},
        'cpl': {'label': 'CPL', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['cpl'], 'formatter': lambda value: _format_currency_br(value)},
        'impressoes': {'label': 'Impressões', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['impressoes'], 'formatter': lambda value: _format_number_br(value, decimals=0)},
        'alcance': {'label': 'Alcance', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['alcance'], 'formatter': lambda value: _format_number_br(value, decimals=0)},
        'ctr': {'label': 'CTR', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['ctr'], 'formatter': lambda value: f'{_format_number_br(value, decimals=2)}%'},
        'taxa_conversao': {'label': 'Taxa de Conversão', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['taxa_conversao'], 'formatter': lambda value: f'{_format_number_br(value, decimals=2)}%'},
        'frequencia': {'label': 'Frequência', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['frequencia'], 'formatter': lambda value: _format_number_br(value, decimals=2)},
        'score_relevancia': {'label': 'Score de Relevância', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['score_relevancia'], 'formatter': lambda value: f'{_format_number_br(value, decimals=1)}/10'},
        'cpm_relativo': {'label': 'CPM relativo', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['cpm_relativo'], 'formatter': lambda value: f'{_format_number_br(value, decimals=2)}x'},
        'resultado_principal': {'label': result_label, 'tooltip': TRAFFIC_METRIC_TOOLTIPS['resultado_principal'], 'formatter': lambda value: _format_number_br(value, decimals=2)},
        'custo_por_resultado': {'label': 'Custo por Resultado', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['custo_por_resultado'], 'formatter': lambda value: _format_currency_br(value)},
        'taxa_resposta': {'label': 'Taxa de Resposta', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['taxa_resposta'], 'formatter': lambda value: f'{_format_number_br(value, decimals=2)}%'},
    }


def _build_traffic_metric_values(summary, previous_summary):
    investimento = Decimal(summary.get('investimento') or 0)
    impressoes = Decimal(summary.get('impressoes') or 0)
    alcance = Decimal(summary.get('alcance') or 0)
    cliques = Decimal(summary.get('cliques') or 0)
    resultados = Decimal(summary.get('resultados') or 0)
    ctr = Decimal(summary.get('ctr') or 0)
    cpc = Decimal(summary.get('cpc') or 0)
    cpm = Decimal(summary.get('cpm') or 0)
    cpl = Decimal(summary.get('cpl') or 0)
    previous_cpm = Decimal(previous_summary.get('cpm') or 0)
    taxa_conversao = (resultados / cliques * Decimal('100')) if cliques else Decimal('0')
    frequencia = (impressoes / alcance) if alcance else Decimal('0')
    taxa_resposta = taxa_conversao
    cpm_relativo = (cpm / previous_cpm) if previous_cpm else Decimal('1')
    score_relevancia = _calculate_relevance_score(ctr, cpc, cpm, frequencia, taxa_conversao)
    return {
        'investimento': investimento,
        'cpm': cpm,
        'cpc': cpc,
        'cpl': cpl,
        'impressoes': impressoes,
        'alcance': alcance,
        'ctr': ctr,
        'taxa_conversao': taxa_conversao,
        'frequencia': frequencia,
        'score_relevancia': score_relevancia,
        'cpm_relativo': cpm_relativo,
        'resultado_principal': resultados,
        'custo_por_resultado': cpl,
        'taxa_resposta': taxa_resposta,
    }


def _build_traffic_blocks(metric_values, previous_metrics, metric_definitions, selected_keys, filter_enabled_map=None):
    blocks = []
    selected_set = set(selected_keys or [])
    filter_enabled_map = filter_enabled_map or {}
    for block in TRAFFIC_BLOCK_DEFINITIONS:
        block_metric_keys = [key for key in block['metrics'] if key in selected_set]
        if not block_metric_keys:
            continue
        rows = []
        for key in block_metric_keys:
            definition = metric_definitions[key]
            current_value = metric_values.get(key, Decimal('0'))
            previous_value = previous_metrics.get(key, Decimal('0'))
            variation_absolute = current_value - previous_value
            variation_percent = (variation_absolute / previous_value * Decimal('100')) if previous_value else None
            variation_class = _resolve_variation_class(key, variation_absolute, variation_percent)
            rows.append(
                {
                    'key': key,
                    'label': definition['label'],
                    'tooltip': definition['tooltip'],
                    'period_value': f"{definition['formatter'](previous_value)} / {definition['formatter'](current_value)}",
                    'current_value': definition['formatter'](current_value),
                    'previous_value': definition['formatter'](previous_value),
                    'variation_value': _format_variation(variation_absolute, variation_percent, key),
                    'variation_class': variation_class,
                }
            )
        blocks.append(
            {
                'key': block['key'],
                'title': block['title'],
                'description': block['description'],
                'highlighted': block['highlighted'],
                'rows': rows,
                'filter_options': [row['label'] for row in rows] if filter_enabled_map.get(block['key']) else [],
            }
        )
    return blocks


def _build_traffic_block_comparison_charts(current_metrics, previous_metrics, metric_definitions, selected_keys):
    selected_set = set(selected_keys or [])
    charts = []
    for block in TRAFFIC_BLOCK_DEFINITIONS:
        chart_metric_keys = block.get('chart_metrics', [])
        metric_keys = [key for key in chart_metric_keys if key in selected_set]
        if not metric_keys:
            continue
        charts.append(
            {
                'key': block['key'],
                'title': f"Comparativo de {block['title']}",
                'highlighted': block['highlighted'],
                'categories': [metric_definitions[key]['label'] for key in metric_keys],
                'series': [
                    {
                        'name': 'Período anterior',
                        'data': [float(previous_metrics.get(key, Decimal('0'))) for key in metric_keys],
                    },
                    {
                        'name': 'Período atual',
                        'data': [float(current_metrics.get(key, Decimal('0'))) for key in metric_keys],
                    },
                ],
            }
        )
    return charts


def _resolve_result_label(config):
    fallback = 'Resultado Principal'
    if not config:
        return fallback
    mapped_column = (config.mapeamento_json or {}).get('tipo_resultado')
    if not mapped_column:
        return fallback
    values = []
    for row in config.preview_json or []:
        value = str(row.get(mapped_column, '')).strip()
        if value:
            values.append(value)
    if not values:
        return fallback
    return max(values, key=values.count)


def _calculate_relevance_score(ctr, cpc, cpm, frequencia, taxa_conversao):
    score = Decimal('0')
    score += Decimal('3') if ctr >= Decimal('1.50') else Decimal('2') if ctr >= Decimal('0.90') else Decimal('1')
    score += Decimal('2') if cpc <= Decimal('1.50') else Decimal('1') if cpc <= Decimal('3.00') else Decimal('0')
    score += Decimal('2') if cpm <= Decimal('30.00') else Decimal('1') if cpm <= Decimal('60.00') else Decimal('0')
    score += Decimal('1.5') if frequencia <= Decimal('2.50') else Decimal('0.5') if frequencia <= Decimal('4.00') else Decimal('0')
    score += Decimal('1.5') if taxa_conversao >= Decimal('8.00') else Decimal('1') if taxa_conversao >= Decimal('3.00') else Decimal('0.5')
    return min(score, Decimal('10'))


def _format_variation(absolute, percent, key):
    if key in {
        'investimento',
        'cpm',
        'cpc',
        'cpl',
        'custo_por_resultado',
        'receita_total',
        'ticket_medio',
        'receita_marketing_pago',
        'receita_marketing_organico',
        'receita_operacional',
        'receita_sem_categoria',
        'resultado_receita_marketing',
        'resultado_receita_operacao',
    }:
        absolute_text = _format_currency_br(absolute)
    elif key in {'ctr', 'taxa_conversao', 'taxa_resposta', 'atendimento_taxa_conversao'}:
        absolute_text = f'{_format_number_br(absolute, decimals=2)}pp'
    elif key == 'taxa_engajamento':
        absolute_text = f'{_format_number_br(absolute, decimals=2)}pp'
    elif key == 'cpm_relativo':
        absolute_text = f'{_format_number_br(absolute, decimals=2)}x'
    elif key == 'score_relevancia':
        absolute_text = _format_number_br(absolute, decimals=1)
    elif key in {
        'vendas_concluidas',
        'conversas',
        'trafego_pago_conversas',
        'organico_conversas',
        'vendas_concluidas_vendedor',
        'atendimentos_vendedor',
        'quantidade_publicacoes',
        'visualizacoes',
        'alcance',
        'curtidas',
        'compartilhamentos',
        'quantidade_posts',
        'visualizacoes_posts',
        'alcance_posts',
        'curtidas_posts',
        'compartilhamentos_posts',
        'quantidade_stories',
        'visualizacoes_stories',
        'alcance_stories',
        'curtidas_stories',
        'compartilhamentos_stories',
        'comentarios',
        'salvamentos',
        'respostas',
        'cliques_link',
        'visitas_perfil',
        'seguimentos',
        'usuarios',
        'novos_usuarios',
        'sessoes',
        'sessoes_engajadas',
        'visualizacoes_pagina',
        'conversoes',
        'presenca_digital_visualizacoes_totais',
        'presenca_digital_alcance_total',
        'presenca_digital_visualizacoes_redes',
        'presenca_digital_impressoes_trafego',
        'presenca_fisica_leads_presenciais',
        'presenca_fisica_oportunidades_presenciais',
        'atendimento_conversas_trafego_pago',
        'atendimento_conversas_organicas',
        'resultado_vendas_marketing',
        'resultado_vendas_operacao',
        'trafego_pago_conversas',
        'organico_conversas',
    }:
        absolute_text = _format_number_br(absolute, decimals=0)
    else:
        absolute_text = _format_number_br(absolute, decimals=2)
    if percent is None:
        return absolute_text
    return f'{absolute_text} ({_format_number_br(percent, decimals=2)}%)'


def _format_currency_br(value):
    return f'R$ {_format_number_br(value, decimals=2)}'


def _format_summary_metric(value, currency=False, suffix=''):
    if currency:
        return _format_currency_br(value)
    if suffix == '%':
        return f'{_format_number_br(value, decimals=2)}%'
    return _format_number_br(value, decimals=0)


def _format_number_br(value, decimals=None):
    if not isinstance(value, Decimal):
        try:
            value = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return str(value)
    if decimals is None:
        decimals = 0 if value == value.to_integral_value() else 2
    text = f'{value:,.{decimals}f}'
    text = text.replace(',', 'X').replace('.', ',').replace('X', '.')
    if decimals > 0:
        text = text.rstrip('0').rstrip(',')
    return text


def _resolve_variation_class(key, absolute, percent):
    if absolute == 0:
        return 'text-muted'
    favorable = None
    if key in TRAFFIC_POSITIVE_WHEN_HIGHER:
        favorable = absolute > 0
    elif key in TRAFFIC_POSITIVE_WHEN_LOWER:
        favorable = absolute < 0
    if favorable is None:
        return 'text-muted'
    threshold = TRAFFIC_PLAUSIBLE_VARIATION_LIMITS.get(key, Decimal('10'))
    if percent is None:
        return 'text-info' if favorable else 'text-warning'
    intensity = abs(percent)
    if favorable:
        return 'text-info' if intensity <= threshold else 'text-success'
    return 'text-warning' if intensity <= threshold else 'text-danger'


def _resolve_crm_variation_class(key, absolute, percent):
    if absolute == 0:
        return 'text-muted'
    if key not in CRM_POSITIVE_WHEN_HIGHER:
        return 'text-muted'
    threshold = CRM_PLAUSIBLE_VARIATION_LIMITS.get(key, Decimal('10'))
    favorable = absolute > 0
    if percent is None:
        return 'text-info' if favorable else 'text-warning'
    intensity = abs(percent)
    if favorable:
        return 'text-info' if intensity <= threshold else 'text-success'
    return 'text-warning' if intensity <= threshold else 'text-danger'


def _resolve_social_variation_class(key, absolute, percent):
    if absolute == 0:
        return 'text-muted'
    if key not in SOCIAL_POSITIVE_WHEN_HIGHER:
        return 'text-muted'
    threshold = SOCIAL_PLAUSIBLE_VARIATION_LIMITS.get(key, Decimal('10'))
    favorable = absolute > 0
    if percent is None:
        return 'text-info' if favorable else 'text-warning'
    intensity = abs(percent)
    if favorable:
        return 'text-info' if intensity <= threshold else 'text-success'
    return 'text-warning' if intensity <= threshold else 'text-danger'
