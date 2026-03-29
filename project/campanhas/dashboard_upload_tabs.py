from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pandas as pd

from empresas.models import ConfiguracaoUploadEmpresa
from empresas.upload_config_services import read_uploaded_dataframe

from .services import campaign_table, summarize_metrics


PAID_TRAFFIC_HINTS = ('meta', 'facebook', 'instagram', 'ads', 'trafego', 'tráfego')


def build_dashboard_upload_tabs(empresa, traffic_queryset, period_start=None, period_end=None):
    configs = {config.tipo_documento: config for config in empresa.configuracoes_upload.exclude(tipo_documento='')}
    traffic_tab = build_traffic_tab(configs.get(ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO), traffic_queryset)
    crm_tab = build_crm_tab(configs.get(ConfiguracaoUploadEmpresa.TipoDocumento.CRM_VENDAS), period_start, period_end)
    leads_tab = build_leads_tab(configs.get(ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS), period_start, period_end)

    tabs = [tab for tab in [traffic_tab, crm_tab, leads_tab] if tab['configured']]
    if tabs:
        tabs.append(build_complete_analysis_tab(traffic_tab, crm_tab, leads_tab))
    return tabs


def build_traffic_tab(config, queryset):
    summary = summarize_metrics(queryset)
    return {
        'key': 'trafego_pago',
        'title': 'Tráfego Pago',
        'configured': bool(config),
        'ready': bool(config) and queryset.exists(),
        'config_name': config.nome if config else '',
        'description': 'Dados consolidados do dashboard atual de campanhas.',
        'kpis': summary,
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
    return {
        'key': 'crm_vendas',
        'title': 'CRM Vendas',
        'configured': True,
        'ready': bool(rows),
        'config_name': config.nome,
        'description': 'Leitura do arquivo configurado para CRM e vendas.',
        'rows': rows[:20],
        'kpis': {
            'registros': len(rows),
            'vendas_fechadas': len(sales_rows),
            'receita_total': total_revenue,
            'ticket_medio': (total_revenue / Decimal(len(sales_rows))) if sales_rows else Decimal('0'),
        },
        'channels': channels,
        'sellers': sellers,
    }


def build_leads_tab(config, period_start=None, period_end=None):
    if not config:
        return _empty_tab('leads_eventos', 'Leads Eventos')
    rows = _read_mapped_rows(config, period_start=period_start, period_end=period_end, date_key='data_evento')
    ages = [_to_decimal(row.get('idade')) for row in rows if row.get('idade') not in ('', None)]
    avg_age = (sum(ages, Decimal('0')) / Decimal(len(ages))) if ages else Decimal('0')
    return {
        'key': 'leads_eventos',
        'title': 'Leads Eventos',
        'configured': True,
        'ready': bool(rows),
        'config_name': config.nome,
        'description': 'Leads captados em eventos a partir do arquivo configurado.',
        'rows': rows[:20],
        'kpis': {
            'leads_total': len(rows),
            'eventos_total': len({row.get('evento') for row in rows if row.get('evento')}),
            'idade_media': avg_age,
        },
        'events': _top_values(rows, 'evento'),
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
