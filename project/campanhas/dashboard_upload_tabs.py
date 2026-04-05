from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
import unicodedata

import pandas as pd

from empresas.models import ConfiguracaoUploadEmpresa
from empresas.upload_config_services import (
    get_category_filter_enabled_map,
    get_enabled_chart_metric_keys,
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
    has_tabs = False
    for config in configs:
        key = f'{config.tipo_documento}_{config.pk}'
        tab = _build_tab_stub(config, traffic_has_data, key)
        has_tabs = True
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
            leads_config = next(
                (config for config in configs if config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS),
                None,
            )
            social_config = next(
                (config for config in configs if config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS),
                None,
            )
            complete_tab = build_complete_analysis_tab_from_configs(
                traffic_config,
                crm_config,
                leads_config,
                social_config,
                traffic_queryset,
                previous_queryset=previous_queryset,
                period_start=period_start,
                period_end=period_end,
                previous_start=previous_start,
                previous_end=previous_end,
            )
        tabs.append(complete_tab)
    return tabs


def _build_tab_stub(config, traffic_has_data, key):
    if config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO:
        ready = bool(config) and traffic_has_data
    elif config.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS:
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
    block_comparison_charts = _build_traffic_block_comparison_charts(derived_metrics, previous_metrics, metric_definitions, selected_chart_keys)
    chart_map = {chart['key']: chart for chart in block_comparison_charts}
    for block in block_cards:
        block['chart'] = chart_map.get(block['key'])
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
    category_blocks = _build_crm_category_blocks(
        selected_table_keys,
        selected_chart_keys,
        current_summary,
        previous_summary,
        filter_enabled_map,
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
        'category_blocks': category_blocks,
    }


def build_leads_tab(config, period_start=None, period_end=None, key='leads_eventos'):
    if not config:
        return _empty_tab('leads_eventos', 'Leads Eventos')
    all_rows = _read_mapped_rows(config, date_key='data_evento')
    rows = _filter_rows_by_period(all_rows, period_start, period_end, 'data_evento')
    ages = [_to_decimal(row.get('idade')) for row in rows if row.get('idade') not in ('', None)]
    avg_age = (sum(ages, Decimal('0')) / Decimal(len(ages))) if ages else Decimal('0')
    kpis = {
        'leads_total': len(rows),
        'eventos_total': len({row.get('evento') for row in rows if row.get('evento')}),
        'idade_media': avg_age,
    }
    return {
        'key': key,
        'panel_type': ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS,
        'title': config.nome,
        'config_id': config.pk,
        'configured': True,
        'ready': bool(rows),
        'config_name': config.nome,
        'description': 'Leads captados em eventos a partir do arquivo configurado.',
        'rows': rows[:20],
        'kpis': kpis,
        'metric_cards': _build_metric_cards(
            kpis,
            get_enabled_table_metric_keys(config.tipo_documento, config.metricas_painel_json),
            {
                'leads_total': ('Total de Leads', lambda value: str(value)),
                'eventos_total': ('Eventos', lambda value: str(value)),
                'idade_media': ('Idade Média', lambda value: f'{value:.1f}'),
            },
        ),
        'events': _top_values(rows, 'evento'),
    }


def build_social_tab(config, period_start=None, period_end=None, previous_start=None, previous_end=None, key='redes_sociais'):
    if not config:
        return _empty_tab('redes_sociais', 'Redes Sociais')
    all_rows = _read_social_rows(config)
    rows = _filter_rows_by_period(all_rows, period_start, period_end, 'data_publicacao')
    selected_table_keys = set(get_enabled_table_metric_keys(config.tipo_documento, config.metricas_painel_json))
    selected_chart_keys = set(get_enabled_chart_metric_keys(config.tipo_documento, config.metricas_painel_json))
    filter_enabled_map = get_category_filter_enabled_map(config.tipo_documento, config.metricas_painel_json)
    current_summary = _social_period_summary(rows)
    previous_rows = _filter_rows_by_period(all_rows, previous_start, previous_end, 'data_publicacao')
    previous_summary = _social_period_summary(previous_rows)
    category_blocks = _build_social_category_blocks(selected_table_keys, selected_chart_keys, current_summary, previous_summary, filter_enabled_map)
    return {
        'key': key,
        'panel_type': ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS,
        'title': config.nome,
        'config_id': config.pk,
        'configured': True,
        'ready': True,
        'config_name': config.nome,
        'description': 'Comparativo do desempenho orgânico entre período atual e anterior, baseado apenas em uploads reais.',
        'rows': rows[:20],
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
    leads_config,
    social_config,
    traffic_queryset,
    previous_queryset=None,
    period_start=None,
    period_end=None,
    previous_start=None,
    previous_end=None,
):
    traffic_summary = summarize_metrics(traffic_queryset)
    previous_traffic_summary = summarize_metrics(previous_queryset) if previous_queryset is not None else {}
    crm_rows = _filter_rows_by_period(_read_mapped_rows(crm_config, date_key='data_contato'), period_start, period_end, 'data_contato') if crm_config else []
    previous_crm_rows = _filter_rows_by_period(_read_mapped_rows(crm_config, date_key='data_contato'), previous_start, previous_end, 'data_contato') if crm_config else []
    crm_summary = _crm_period_summary(crm_rows, {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}, crm_config) if crm_config else {'geral': {}, 'origem': {}}
    previous_crm_summary = _crm_period_summary(previous_crm_rows, {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}, crm_config) if crm_config else {'geral': {}, 'origem': {}}
    leads_rows = _filter_rows_by_period(_read_mapped_rows(leads_config, date_key='data_evento'), period_start, period_end, 'data_evento') if leads_config else []
    social_rows = _filter_rows_by_period(_read_social_rows(social_config), period_start, period_end, 'data_publicacao') if social_config else []
    previous_social_rows = _filter_rows_by_period(_read_social_rows(social_config), previous_start, previous_end, 'data_publicacao') if social_config else []
    social_summary = _social_period_summary(social_rows) if social_config else {}
    previous_social_summary = _social_period_summary(previous_social_rows) if social_config else {}
    competitor_signals = _build_competitor_signals(traffic_config.empresa if traffic_config else (crm_config.empresa if crm_config else None))

    marketing_rows = [row for row in crm_rows if _is_marketing_sale(row, crm_config)]
    previous_marketing_rows = [row for row in previous_crm_rows if _is_marketing_sale(row, crm_config)]
    operacao_rows = [row for row in crm_rows if _is_operacao_sale(row)]
    previous_operacao_rows = [row for row in previous_crm_rows if _is_operacao_sale(row)]
    cliente_base_rows = [row for row in crm_rows if _is_cliente_base_sale(row)]
    previous_cliente_base_rows = [row for row in previous_crm_rows if _is_cliente_base_sale(row)]
    cliente_base_marketing_share = Decimal('0.30')
    marketing_revenue = sum((_to_decimal(row.get('valor_venda')) for row in marketing_rows), Decimal('0'))
    previous_marketing_revenue = sum((_to_decimal(row.get('valor_venda')) for row in previous_marketing_rows), Decimal('0'))
    operacao_revenue = sum((_to_decimal(row.get('valor_venda')) for row in operacao_rows), Decimal('0'))
    previous_operacao_revenue = sum((_to_decimal(row.get('valor_venda')) for row in previous_operacao_rows), Decimal('0'))
    cliente_base_revenue = sum((_to_decimal(row.get('valor_venda')) for row in cliente_base_rows), Decimal('0'))
    previous_cliente_base_revenue = sum((_to_decimal(row.get('valor_venda')) for row in previous_cliente_base_rows), Decimal('0'))
    marketing_revenue += cliente_base_revenue * cliente_base_marketing_share
    previous_marketing_revenue += previous_cliente_base_revenue * cliente_base_marketing_share
    operacao_revenue -= cliente_base_revenue * cliente_base_marketing_share
    previous_operacao_revenue -= previous_cliente_base_revenue * cliente_base_marketing_share
    marketing_sales = sum(1 for row in marketing_rows if _crm_is_closed_sale(row, {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}))
    previous_marketing_sales = sum(1 for row in previous_marketing_rows if _crm_is_closed_sale(row, {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}))
    operacao_sales = sum(1 for row in operacao_rows if _crm_is_closed_sale(row, {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}))
    previous_operacao_sales = sum(1 for row in previous_operacao_rows if _crm_is_closed_sale(row, {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}))

    summary_panels = [
        _build_summary_panel(
            'presenca_digital',
            'Presença Digital',
            'Soma de redes sociais com tráfego pago para leitura consolidada de alcance digital.',
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
            chart_metric_keys=['atendimento_conversas_trafego_pago', 'atendimento_conversas_organicas'],
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
        'ready': bool(traffic_queryset.exists() or crm_rows or leads_rows or social_rows or crm_config or social_config),
        'description': 'Painel cruzado geral entre presença digital, atendimento e resultado.',
        'top_cards': [
            {
                'label': 'Alcance Digital',
                'value': _format_number_br(
                    Decimal(traffic_summary.get('alcance') or 0) + (social_summary.get('alcance') or Decimal('0')),
                    decimals=0,
                ),
            },
            {
                'label': 'Alcance Físico',
                'value': _format_number_br(Decimal('0'), decimals=0),
            },
            {
                'label': 'Taxa de Conversão',
                'value': f"{_format_number_br(crm_summary.get('geral', {}).get('taxa_conversao', Decimal('0')), decimals=2)}%",
            },
            {
                'label': 'Receita Marketing',
                'value': _format_currency_br(marketing_revenue),
            },
        ],
        'summary_panels': summary_panels,
        'competitor_signals': competitor_signals,
    }


def _build_summary_panel(key, title, description, metrics, chart_metric_keys=None):
    rows = []
    categories = []
    previous_data = []
    current_data = []
    chart_metric_keys = set(chart_metric_keys or [metric_key for metric_key, *_ in metrics])
    for metric_key, label, previous_value, current_value, currency, suffix in metrics:
        previous_decimal = _to_decimal(previous_value)
        current_decimal = _to_decimal(current_value)
        variation_absolute = current_decimal - previous_decimal
        variation_percent = (variation_absolute / previous_decimal * Decimal('100')) if previous_decimal else None
        rows.append(
            {
                'label': label,
                'period_value': f"{_format_summary_metric(previous_decimal, currency, suffix)} / {_format_summary_metric(current_decimal, currency, suffix)}",
                'variation_value': _format_variation(variation_absolute, variation_percent, metric_key),
                'variation_class': _resolve_crm_variation_class(metric_key, variation_absolute, variation_percent),
            }
        )
        if metric_key in chart_metric_keys:
            categories.append(label)
            previous_data.append(_decimal_to_float(previous_decimal))
            current_data.append(_decimal_to_float(current_decimal))

    chart = None
    if categories:
        chart = {
            'key': f'executive_{key}',
            'title': title,
            'categories': categories,
            'series': [
                {'name': 'Período anterior', 'data': previous_data},
                {'name': 'Período atual', 'data': current_data},
            ],
        }

    return {
        'key': key,
        'title': title,
        'description': description,
        'rows': rows,
        'chart': chart,
        'chart_type': 'bar_compare',
        'filter_options': [],
    }


def _build_social_category_blocks(selected_table_keys, selected_chart_keys, current_summary, previous_summary, filter_enabled_map=None):
    filter_enabled_map = filter_enabled_map or {}
    blocks = []
    definitions = [
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
    for key, title, description, metric_defs, chart_defaults in definitions:
        rows = _social_comparison_rows(metric_defs, current_summary, previous_summary, selected_table_keys)
        metric_keys = {item[0] for item in metric_defs}
        chart_keys = [item for item in chart_defaults if item in selected_chart_keys]
        if not chart_keys:
            chart_keys = [key_item for key_item, _, _, _ in metric_defs if key_item in selected_table_keys]
        chart = _social_comparison_chart(f'social_{key}', title, metric_defs, current_summary, previous_summary, chart_keys)
        if rows or chart:
            blocks.append(
                {
                    'key': key,
                    'title': title,
                    'description': description,
                    'rows': rows,
                    'chart': chart,
                    'chart_type': 'bar_compare',
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


def _build_crm_category_blocks(selected_table_keys, selected_chart_keys, current_summary, previous_summary, filter_enabled_map=None):
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
    resultado_metric_keys = {item[0] for item in resultado_metrics}
    resultado_chart_keys = {key for key in selected_chart_keys if key in resultado_metric_keys}
    if not resultado_chart_keys:
        resultado_chart_keys = {key for key in selected_table_keys if key in resultado_metric_keys}
    resultado_chart = _crm_comparison_chart('crm_resultado', 'Resultado', resultado_metrics, current_summary['geral'], previous_summary['geral'], resultado_chart_keys)
    if resultado_rows or resultado_chart:
        blocks.append(
            {
                'key': 'resultado',
                'title': 'Resultado',
                'description': 'Comparativo principal entre os períodos do comercial.',
                'rows': resultado_rows,
                'chart': resultado_chart,
                'chart_type': 'bar_compare',
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
    origem_chart = _crm_distribution_pie_chart(
        {
            'Marketing Pago': current_summary['origem'].get('receita_marketing_pago', Decimal('0')),
            'Marketing Orgânico': current_summary['origem'].get('receita_marketing_organico', Decimal('0')),
            'Operacional': current_summary['origem'].get('receita_operacional', Decimal('0')),
            'Sem categoria': current_summary['origem'].get('receita_sem_categoria', Decimal('0')),
        },
        'crm_origem',
        'Origem',
        _crm_origin_color,
    ) if origem_chart_enabled else None
    if origem_rows or origem_chart:
        blocks.append(
            {
                'key': 'origem',
                'title': 'Origem',
                'description': 'Distribuição da receita entre marketing pago, marketing orgânico, operação e itens sem categoria.',
                'rows': origem_rows,
                'chart': origem_chart,
                'chart_type': 'pie',
                'filter_options': [row['label'] for row in origem_rows] if filter_enabled_map.get('origem') else [],
            }
        )

    status_rows = _crm_status_comparison_rows(
        current_summary['status_counts'],
        previous_summary['status_counts'],
        'status_fechamento' in selected_table_keys,
    )
    status_chart_enabled = 'status_fechamento' in selected_chart_keys or ('status_fechamento' in selected_table_keys and 'status_fechamento' not in selected_chart_keys)
    status_chart = _crm_status_pie_chart(current_summary['status']) if status_chart_enabled else None
    if status_rows or status_chart:
        blocks.append(
            {
                'key': 'status',
                'title': 'Status',
                'description': 'Distribuição atual em pizza e comparação por status na tabela.',
                'rows': status_rows,
                'chart': status_chart,
                'chart_type': 'pie',
                'filter_options': [row['label'] for row in status_rows] if filter_enabled_map.get('status') else [],
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
    uploads = _get_panel_uploads(config)
    for upload in uploads:
        upload_type = getattr(upload, 'tipo_upload', '') or _normalize_social_content_type('', '', upload.nome_arquivo)
        social_mapping = (config.mapeamento_json or {}).get(upload_type, {})
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
    parsed = pd.to_datetime(value, errors='coerce', dayfirst=True)
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


def _social_period_summary(rows):
    def sum_key(dataset, field):
        return sum((_to_decimal(item.get(field)) for item in dataset), Decimal('0'))

    posts = [row for row in rows if row.get('tipo_conteudo_normalizado') == 'post']
    stories = [row for row in rows if row.get('tipo_conteudo_normalizado') == 'story']
    return {
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
    }


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
