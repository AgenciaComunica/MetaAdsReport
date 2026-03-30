from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pandas as pd

from empresas.models import ConfiguracaoUploadEmpresa
from empresas.upload_config_services import read_uploaded_dataframe

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


def build_dashboard_upload_tabs(empresa, traffic_queryset, period_start=None, period_end=None, previous_queryset=None):
    configs = {config.tipo_documento: config for config in empresa.configuracoes_upload.exclude(tipo_documento='')}
    traffic_tab = build_traffic_tab(
        configs.get(ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO),
        traffic_queryset,
        previous_queryset=previous_queryset,
    )
    crm_tab = build_crm_tab(configs.get(ConfiguracaoUploadEmpresa.TipoDocumento.CRM_VENDAS), period_start, period_end)
    leads_tab = build_leads_tab(configs.get(ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS), period_start, period_end)
    social_tab = build_social_tab(configs.get(ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS), period_start, period_end)

    tabs = [tab for tab in [traffic_tab, crm_tab, leads_tab, social_tab] if tab['configured']]
    if tabs:
        tabs.append(build_complete_analysis_tab(traffic_tab, crm_tab, leads_tab))
    return tabs


def build_traffic_tab(config, queryset, previous_queryset=None):
    summary = summarize_metrics(queryset)
    previous_summary = summarize_metrics(previous_queryset) if previous_queryset is not None else {}
    result_label = _resolve_result_label(config)
    derived_metrics = _build_traffic_metric_values(summary, previous_summary)
    metric_definitions = _build_traffic_metric_definitions(result_label)
    selected_keys = list(config.metricas_painel_json or []) if config else []
    previous_metrics = _build_traffic_metric_values(previous_summary, {})
    block_cards = _build_traffic_blocks(derived_metrics, previous_metrics, metric_definitions, selected_keys)
    block_comparison_charts = _build_traffic_block_comparison_charts(derived_metrics, previous_metrics, metric_definitions, selected_keys)
    return {
        'key': 'trafego_pago',
        'title': config.nome if config else 'Tráfego Pago',
        'config_id': config.pk if config else None,
        'configured': bool(config),
        'ready': bool(config) and queryset.exists(),
        'config_name': config.nome if config else '',
        'description': 'Dados consolidados do dashboard atual de campanhas.',
        'kpis': summary,
        'result_label': result_label,
        'metric_blocks': block_cards,
        'block_comparison_charts': block_comparison_charts,
        'campaign_rows': campaign_table(queryset),
    }


def build_crm_tab(config, period_start=None, period_end=None):
    if not config:
        return _empty_tab('crm_vendas', 'CRM Vendas')
    rows = _read_mapped_rows(config, period_start=period_start, period_end=period_end, date_key='data_contato')
    total_revenue = sum((_to_decimal(row.get('valor_venda')) for row in rows), Decimal('0'))
    closed_status = {'ganho', 'fechado', 'fechada', 'venda', 'vendido'}
    sales_rows = [row for row in rows if str(row.get('status_fechamento', '')).strip().lower() in closed_status]
    channels = _top_values(rows, 'canal')
    sellers = _top_values(rows, 'vendedor')
    kpis = {
        'registros': len(rows),
        'vendas_fechadas': len(sales_rows),
        'receita_total': total_revenue,
        'ticket_medio': (total_revenue / Decimal(len(sales_rows))) if sales_rows else Decimal('0'),
    }
    return {
        'key': 'crm_vendas',
        'title': config.nome,
        'config_id': config.pk,
        'configured': True,
        'ready': bool(rows),
        'config_name': config.nome,
        'description': 'Leitura do arquivo configurado para CRM e vendas.',
        'rows': rows[:20],
        'kpis': kpis,
        'metric_cards': _build_metric_cards(
            kpis,
            config.metricas_painel_json,
            {
                'registros': ('Registros', lambda value: str(value)),
                'vendas_fechadas': ('Vendas Fechadas', lambda value: str(value)),
                'receita_total': ('Receita Total', lambda value: f'R$ {value:.2f}'),
                'ticket_medio': ('Ticket Médio', lambda value: f'R$ {value:.2f}'),
            },
        ),
        'channels': channels,
        'sellers': sellers,
    }


def build_leads_tab(config, period_start=None, period_end=None):
    if not config:
        return _empty_tab('leads_eventos', 'Leads Eventos')
    rows = _read_mapped_rows(config, period_start=period_start, period_end=period_end, date_key='data_evento')
    ages = [_to_decimal(row.get('idade')) for row in rows if row.get('idade') not in ('', None)]
    avg_age = (sum(ages, Decimal('0')) / Decimal(len(ages))) if ages else Decimal('0')
    kpis = {
        'leads_total': len(rows),
        'eventos_total': len({row.get('evento') for row in rows if row.get('evento')}),
        'idade_media': avg_age,
    }
    return {
        'key': 'leads_eventos',
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
            config.metricas_painel_json,
            {
                'leads_total': ('Total de Leads', lambda value: str(value)),
                'eventos_total': ('Eventos', lambda value: str(value)),
                'idade_media': ('Idade Média', lambda value: f'{value:.1f}'),
            },
        ),
        'events': _top_values(rows, 'evento'),
    }


def build_social_tab(config, period_start=None, period_end=None):
    if not config:
        return _empty_tab('redes_sociais', 'Redes Sociais')
    rows = _read_mapped_rows(config, period_start=period_start, period_end=period_end, date_key='data_referencia')
    kpis = {
        'perfis_total': len({row.get('perfil') for row in rows if row.get('perfil')}),
        'seguidores_total': sum((_to_decimal(row.get('seguidores')) for row in rows), Decimal('0')),
        'publicacoes_total': sum((_to_decimal(row.get('publicacoes')) for row in rows), Decimal('0')),
        'engajamento_total': sum((_to_decimal(row.get('engajamento')) for row in rows), Decimal('0')),
    }
    return {
        'key': 'redes_sociais',
        'title': config.nome,
        'config_id': config.pk,
        'configured': True,
        'ready': bool(rows),
        'config_name': config.nome,
        'description': 'Indicadores importados para monitoramento de redes sociais.',
        'rows': rows[:20],
        'kpis': kpis,
        'metric_cards': _build_metric_cards(
            kpis,
            config.metricas_painel_json,
            {
                'perfis_total': ('Perfis', lambda value: str(value)),
                'seguidores_total': ('Seguidores', lambda value: str(int(value) if value == int(value) else value)),
                'publicacoes_total': ('Publicações', lambda value: str(int(value) if value == int(value) else value)),
                'engajamento_total': ('Engajamento', lambda value: str(int(value) if value == int(value) else value)),
            },
        ),
        'social_networks': _top_values(rows, 'rede_social'),
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
        'title': 'Análise Completa',
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


def _empty_tab(key, title):
    return {
        'key': key,
        'title': title,
        'configured': False,
        'ready': False,
        'config_name': '',
        'description': '',
    }


def _read_mapped_rows(config, period_start=None, period_end=None, date_key=''):
    if not config or not config.arquivo_exemplo or not config.mapeamento_json:
        return []
    dataframe = read_uploaded_dataframe(config.arquivo_exemplo.path, config.nome_arquivo_exemplo or config.arquivo_exemplo.name)
    rows = []
    for _, source_row in dataframe.iterrows():
        row = {}
        for field_key, column_name in (config.mapeamento_json or {}).items():
            row[field_key] = _serialize_value(source_row.get(column_name, ''))
        if date_key and period_start and period_end:
            row_date = _parse_date(row.get(date_key))
            if row_date is not None and not (period_start <= row_date <= period_end):
                continue
        rows.append(row)
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


def _top_values(rows, key):
    counts = {}
    for row in rows:
        value = str(row.get(key, '')).strip()
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]


def _is_paid_traffic_sale(row):
    haystack = ' '.join(
        [
            str(row.get('origem_lead', '')),
            str(row.get('canal', '')),
            str(row.get('tag_lead', '')),
        ]
    ).lower()
    return any(term in haystack for term in PAID_TRAFFIC_HINTS)


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
        'investimento': {'label': 'Investimento Total', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['investimento'], 'formatter': lambda value: f'R$ {value:.2f}'},
        'cpm': {'label': 'CPM', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['cpm'], 'formatter': lambda value: f'R$ {value:.2f}'},
        'cpc': {'label': 'CPC', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['cpc'], 'formatter': lambda value: f'R$ {value:.2f}'},
        'cpl': {'label': 'CPL', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['cpl'], 'formatter': lambda value: f'R$ {value:.2f}'},
        'impressoes': {'label': 'Impressões', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['impressoes'], 'formatter': lambda value: f'{int(value)}'},
        'alcance': {'label': 'Alcance', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['alcance'], 'formatter': lambda value: f'{int(value)}'},
        'ctr': {'label': 'CTR', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['ctr'], 'formatter': lambda value: f'{value:.2f}%'},
        'taxa_conversao': {'label': 'Taxa de Conversão', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['taxa_conversao'], 'formatter': lambda value: f'{value:.2f}%'},
        'frequencia': {'label': 'Frequência', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['frequencia'], 'formatter': lambda value: f'{value:.2f}'},
        'score_relevancia': {'label': 'Score de Relevância', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['score_relevancia'], 'formatter': lambda value: f'{value:.1f}/10'},
        'cpm_relativo': {'label': 'CPM relativo', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['cpm_relativo'], 'formatter': lambda value: f'{value:.2f}x'},
        'resultado_principal': {'label': result_label, 'tooltip': TRAFFIC_METRIC_TOOLTIPS['resultado_principal'], 'formatter': lambda value: f'{value:.2f}'},
        'custo_por_resultado': {'label': 'Custo por Resultado', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['custo_por_resultado'], 'formatter': lambda value: f'R$ {value:.2f}'},
        'taxa_resposta': {'label': 'Taxa de Resposta', 'tooltip': TRAFFIC_METRIC_TOOLTIPS['taxa_resposta'], 'formatter': lambda value: f'{value:.2f}%'},
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


def _build_traffic_blocks(metric_values, previous_metrics, metric_definitions, selected_keys):
    blocks = []
    selected_set = set(selected_keys or [])
    for block in TRAFFIC_BLOCK_DEFINITIONS:
        block_metric_keys = [key for key in block['metrics'] if not selected_set or key in selected_set]
        if not block_metric_keys:
            block_metric_keys = list(block['metrics'])
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
            }
        )
    return blocks


def _build_traffic_block_comparison_charts(current_metrics, previous_metrics, metric_definitions, selected_keys):
    selected_set = set(selected_keys or [])
    charts = []
    for block in TRAFFIC_BLOCK_DEFINITIONS:
        chart_metric_keys = block.get('chart_metrics', [])
        metric_keys = [key for key in chart_metric_keys if not selected_set or key in selected_set]
        if not metric_keys:
            metric_keys = list(chart_metric_keys)
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
    if key in {'investimento', 'cpm', 'cpc', 'cpl', 'custo_por_resultado'}:
        absolute_text = f'R$ {absolute:.2f}'
    elif key in {'ctr', 'taxa_conversao', 'taxa_resposta'}:
        absolute_text = f'{absolute:.2f}pp'
    elif key == 'cpm_relativo':
        absolute_text = f'{absolute:.2f}x'
    elif key == 'score_relevancia':
        absolute_text = f'{absolute:.1f}'
    else:
        absolute_text = f'{absolute:.2f}' if isinstance(absolute, Decimal) else str(absolute)
    if percent is None:
        return absolute_text
    return f'{absolute_text} ({percent:.2f}%)'


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
