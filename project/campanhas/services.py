from __future__ import annotations

import math
from hashlib import sha256
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import pandas as pd
from django.db.models import Avg, Sum

from .models import CampanhaMetric


COLUMN_ALIASES = {
    'campaign_name': ['campaign name', 'nome da campanha', 'campanha', 'campaign', 'ad set name', 'anúncios', 'anuncios', 'ad name'],
    'date': ['date', 'data', 'day', 'dia', 'reporting starts', 'reporting ends', 'início dos relatórios', 'inicio dos relatórios', 'término dos relatórios', 'termino dos relatórios'],
    'amount_spent': ['amount spent', 'valor gasto', 'gasto', 'investimento', 'spend', 'valor usado', 'valor usado brl', 'valor usado (brl)'],
    'impressions': ['impressions', 'impressões', 'impressoes'],
    'reach': ['reach', 'alcance'],
    'link_clicks': ['link clicks', 'clicks', 'cliques no link', 'cliques', 'click'],
    'ctr': ['ctr', 'ctr (all)', 'unique ctr', 'ctr (todos)'],
    'cpc': ['cpc', 'cpc (all)', 'cost per click', 'cpc (custo por clique no link)'],
    'cpm': ['cpm', 'custo por mil', 'cost per 1,000 impressions', 'cpm (custo por 1.000 impressões)', 'cpm (custo por 1.000 impressoes)'],
    'results': ['results', 'leads', 'conversões', 'conversoes', 'conversions', 'purchases', 'resultados'],
}


DISPLAY_LABELS = {
    'campaign_name': 'Campanha',
    'date': 'Data',
    'amount_spent': 'Investimento',
    'investimento': 'Investimento',
    'impressions': 'Impressões',
    'impressoes': 'Impressões',
    'reach': 'Alcance',
    'alcance': 'Alcance',
    'link_clicks': 'Cliques',
    'cliques': 'Cliques',
    'ctr': 'CTR',
    'cpc': 'CPC',
    'cpm': 'CPM',
    'results': 'Resultados',
    'resultados': 'Resultados',
    'cpl': 'CPL',
}


@dataclass
class ImportResult:
    imported_count: int
    duplicate_in_file_count: int
    duplicate_existing_count: int
    mapping: dict
    warnings: list[str]
    missing_required: list[str]
    detected_columns: list[str]


def normalize_header(value):
    return ''.join(ch.lower() if ch.isalnum() else ' ' for ch in str(value)).strip()


def read_table(file_path):
    errors = []
    for encoding in ['utf-8-sig', 'utf-8', 'latin1', 'cp1252']:
        try:
            df = pd.read_csv(file_path, sep=None, engine='python', encoding=encoding)
            return df
        except Exception as exc:  # pragma: no cover - defensive I/O fallback
            errors.append(f'{encoding}: {exc}')
    raise ValueError('Falha ao ler o arquivo CSV. Verifique encoding, separador e cabeçalhos.')


def suggest_mapping(columns):
    normalized = {column: normalize_header(column) for column in columns}
    mapping = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        candidates = [normalize_header(alias) for alias in aliases]
        for original, norm in normalized.items():
            if norm in candidates:
                mapping[canonical] = original
                break
    return mapping


def parse_decimal(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return Decimal('0')
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    text = str(value).strip()
    if not text:
        return Decimal('0')
    text = text.replace('%', '').replace('R$', '').replace(' ', '')
    if ',' in text and '.' in text:
        if text.rfind(',') > text.rfind('.'):
            text = text.replace('.', '').replace(',', '.')
        else:
            text = text.replace(',', '')
    elif ',' in text:
        text = text.replace('.', '').replace(',', '.')
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal('0')


def parse_int(value):
    return int(parse_decimal(value))


def parse_date(value):
    if value is None or value == '':
        return None
    parsed = pd.to_datetime(value, errors='coerce', dayfirst=True)
    if pd.isna(parsed):
        return None
    return parsed.date()


def metric_fingerprint(empresa_id, data, campanha, investimento, impressoes, alcance, cliques, ctr, cpc, cpm, resultados):
    payload = '|'.join(
        [
            str(empresa_id),
            data.isoformat() if data else '',
            campanha.strip().lower(),
            str(investimento),
            str(impressoes),
            str(alcance),
            str(cliques),
            str(ctr),
            str(cpc),
            str(cpm),
            str(resultados),
        ]
    )
    return sha256(payload.encode('utf-8')).hexdigest()


def import_metrics_from_upload(upload, manual_mapping=None):
    df = read_table(upload.arquivo.path)
    df = df.dropna(how='all')
    df.columns = [str(column).strip() for column in df.columns]
    mapping = suggest_mapping(df.columns)
    if manual_mapping:
        mapping.update({key: value for key, value in manual_mapping.items() if value})

    missing_required = []
    if 'campaign_name' not in mapping:
        missing_required.append('campaign_name')
    if missing_required:
        return ImportResult(
            imported_count=0,
            duplicate_in_file_count=0,
            duplicate_existing_count=0,
            mapping=mapping,
            warnings=[],
            missing_required=missing_required,
            detected_columns=list(df.columns),
        )

    upload.metricas.all().delete()
    batch = []
    warnings = []
    duplicate_in_file_count = 0
    duplicate_existing_count = 0
    seen_in_file = set()
    existing_fingerprints = set(
        CampanhaMetric.objects.filter(upload__empresa=upload.empresa)
        .exclude(upload=upload)
        .exclude(fingerprint='')
        .values_list('fingerprint', flat=True)
    )

    for _, row in df.iterrows():
        campaign_name = str(row.get(mapping['campaign_name'], '')).strip()
        if not campaign_name:
            continue
        investimento = parse_decimal(row.get(mapping.get('amount_spent')))
        impressoes = parse_int(row.get(mapping.get('impressions')))
        alcance = parse_int(row.get(mapping.get('reach')))
        cliques = parse_int(row.get(mapping.get('link_clicks')))
        resultados = parse_decimal(row.get(mapping.get('results')))

        ctr = parse_decimal(row.get(mapping.get('ctr')))
        cpc = parse_decimal(row.get(mapping.get('cpc')))
        cpm = parse_decimal(row.get(mapping.get('cpm')))
        data = parse_date(row.get(mapping.get('date'))) or upload.data_inicio

        if not ctr and impressoes:
            ctr = (Decimal(cliques) / Decimal(impressoes)) * Decimal('100')
        if not cpc and cliques:
            cpc = investimento / Decimal(cliques)
        if not cpm and impressoes:
            cpm = (investimento / Decimal(impressoes)) * Decimal('1000')
        cpl = Decimal('0')
        if resultados:
            cpl = investimento / resultados

        fingerprint = metric_fingerprint(
            upload.empresa_id,
            data,
            campaign_name,
            investimento,
            impressoes,
            alcance,
            cliques,
            ctr,
            cpc,
            cpm,
            resultados,
        )
        if fingerprint in seen_in_file:
            duplicate_in_file_count += 1
            continue
        if fingerprint in existing_fingerprints:
            duplicate_existing_count += 1
            continue
        seen_in_file.add(fingerprint)

        batch.append(
            CampanhaMetric(
                upload=upload,
                fingerprint=fingerprint,
                data=data,
                campanha=campaign_name[:255],
                investimento=investimento,
                impressoes=impressoes,
                alcance=alcance,
                cliques=cliques,
                ctr=ctr,
                cpc=cpc,
                cpm=cpm,
                resultados=resultados,
                cpl=cpl,
            )
        )

    CampanhaMetric.objects.bulk_create(batch, batch_size=500)
    if 'date' not in mapping and not upload.data_inicio:
        warnings.append('Arquivo sem coluna de data; use o período manual para análises temporais mais precisas.')
    if duplicate_in_file_count:
        warnings.append(f'{duplicate_in_file_count} linha(s) duplicada(s) no mesmo arquivo foram ignoradas.')
    if duplicate_existing_count:
        warnings.append(f'{duplicate_existing_count} linha(s) já existentes em uploads anteriores da empresa foram ignoradas.')

    return ImportResult(
        imported_count=len(batch),
        duplicate_in_file_count=duplicate_in_file_count,
        duplicate_existing_count=duplicate_existing_count,
        mapping=mapping,
        warnings=warnings,
        missing_required=[],
        detected_columns=list(df.columns),
    )


def metrics_queryset(empresa=None, data_inicio=None, data_fim=None):
    queryset = CampanhaMetric.objects.select_related('upload', 'upload__empresa')
    if empresa:
        queryset = queryset.filter(upload__empresa=empresa)
    if data_inicio:
        queryset = queryset.filter(data__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(data__lte=data_fim)
    return queryset


def summarize_metrics(queryset):
    totals = queryset.aggregate(
        investimento=Sum('investimento'),
        impressoes=Sum('impressoes'),
        alcance=Sum('alcance'),
        cliques=Sum('cliques'),
        resultados=Sum('resultados'),
    )
    investimento = totals['investimento'] or Decimal('0')
    impressoes = totals['impressoes'] or 0
    cliques = totals['cliques'] or 0
    resultados = totals['resultados'] or Decimal('0')
    ctr = (Decimal(cliques) / Decimal(impressoes) * Decimal('100')) if impressoes else Decimal('0')
    cpc = (investimento / Decimal(cliques)) if cliques else Decimal('0')
    cpm = (investimento / Decimal(impressoes) * Decimal('1000')) if impressoes else Decimal('0')
    cpl = (investimento / resultados) if resultados else Decimal('0')
    totals.update({'ctr': ctr, 'cpc': cpc, 'cpm': cpm, 'cpl': cpl})
    return totals


def campaign_table(queryset):
    rows = []
    for item in queryset.values('campanha').annotate(
        investimento=Sum('investimento'),
        impressoes=Sum('impressoes'),
        alcance=Sum('alcance'),
        cliques=Sum('cliques'),
        resultados=Sum('resultados'),
        ctr_medio=Avg('ctr'),
    ).order_by('-investimento'):
        cliques = item['cliques'] or 0
        impressoes = item['impressoes'] or 0
        investimento = item['investimento'] or Decimal('0')
        resultados = item['resultados'] or Decimal('0')
        rows.append(
            {
                'campanha': item['campanha'],
                'investimento': investimento,
                'impressoes': impressoes,
                'alcance': item['alcance'] or 0,
                'cliques': cliques,
                'ctr': (Decimal(cliques) / Decimal(impressoes) * Decimal('100')) if impressoes else Decimal('0'),
                'cpc': (investimento / Decimal(cliques)) if cliques else Decimal('0'),
                'cpm': (investimento / Decimal(impressoes) * Decimal('1000')) if impressoes else Decimal('0'),
                'resultados': resultados,
                'cpl': (investimento / resultados) if resultados else Decimal('0'),
            }
        )
    return rows


def campaign_comparison_table(current_qs, previous_qs):
    current_rows = {row['campanha']: row for row in campaign_table(current_qs)}
    previous_rows = {row['campanha']: row for row in campaign_table(previous_qs)}

    campaign_names = sorted(
        set(current_rows) | set(previous_rows),
        key=lambda name: (
            (current_rows.get(name, {}).get('investimento') or Decimal('0')) +
            (previous_rows.get(name, {}).get('investimento') or Decimal('0'))
        ),
        reverse=True,
    )

    metrics = ['investimento', 'impressoes', 'cliques', 'ctr', 'resultados', 'cpl']
    rows = []
    for campaign in campaign_names:
        current = current_rows.get(campaign, {})
        previous = previous_rows.get(campaign, {})
        row = {'campanha': campaign}
        for metric in metrics:
            row[f'{metric}_atual'] = current.get(metric, 0)
            row[f'{metric}_anterior'] = previous.get(metric, 0)
        rows.append(row)
    return rows


def timeline_data(queryset):
    grouped = {}
    for metric in queryset.order_by('data'):
        label = metric.data.isoformat() if metric.data else 'Sem data'
        grouped.setdefault(label, Decimal('0'))
        grouped[label] += metric.investimento
    return {
        'labels': list(grouped.keys()),
        'values': [float(value) for value in grouped.values()],
    }


def monthly_comparison_chart(current_qs, previous_qs):
    def summarize_by_month(queryset):
        grouped = {}
        for metric in queryset.exclude(data__isnull=True).order_by('data'):
            label = metric.data.strftime('%m/%Y')
            grouped.setdefault(label, Decimal('0'))
            grouped[label] += metric.investimento
        return grouped

    current_grouped = summarize_by_month(current_qs)
    previous_grouped = summarize_by_month(previous_qs)
    labels = list(dict.fromkeys([*current_grouped.keys(), *previous_grouped.keys()]))
    return {
        'labels': labels,
        'current_values': [float(current_grouped.get(label, Decimal('0'))) for label in labels],
        'previous_values': [float(previous_grouped.get(label, Decimal('0'))) for label in labels],
    }


def stacked_campaign_comparison_chart(current_qs, previous_qs, metric_key='resultados', limit=4):
    current_rows = {
        item['campanha']: item.get(metric_key) or Decimal('0')
        for item in campaign_table(current_qs)
    }
    previous_rows = {
        item['campanha']: item.get(metric_key) or Decimal('0')
        for item in campaign_table(previous_qs)
    }

    ranked_campaigns = sorted(
        set(current_rows) | set(previous_rows),
        key=lambda name: (current_rows.get(name, Decimal('0')) + previous_rows.get(name, Decimal('0'))),
        reverse=True,
    )[:limit]

    current_palette = ['#b7e4c7', '#52b788', '#2d6a4f', '#1b4332']
    previous_palette = ['#caf0f8', '#90e0ef', '#48cae4', '#0077b6']
    series = []
    for index, campaign in enumerate(ranked_campaigns):
        series.append(
            {
                'name': f'{campaign} - Atual',
                'data': [
                    float(current_rows.get(campaign, Decimal('0'))),
                    0,
                ],
                'color': current_palette[index % len(current_palette)],
            }
        )
        series.append(
            {
                'name': f'{campaign} - Anterior',
                'data': [
                    0,
                    float(previous_rows.get(campaign, Decimal('0'))),
                ],
                'color': previous_palette[index % len(previous_palette)],
            }
        )

    return {
        'categories': ['Período atual', 'Período anterior'],
        'series': series,
        'metric_label': DISPLAY_LABELS.get(metric_key, metric_key.upper()),
        'metric_key': metric_key,
    }


def comparison_summary(current_qs, previous_qs):
    current = summarize_metrics(current_qs)
    previous = summarize_metrics(previous_qs)
    keys = ['investimento', 'ctr', 'cpc', 'cpm', 'resultados', 'cpl']
    comparison = []
    for key in keys:
        atual = current.get(key) or Decimal('0')
        anterior = previous.get(key) or Decimal('0')
        variacao_absoluta = atual - anterior
        variacao_percentual = (variacao_absoluta / anterior * Decimal('100')) if anterior else None
        comparison.append(
            {
                'label': DISPLAY_LABELS.get(key, key.upper()),
                'key': key,
                'atual': atual,
                'anterior': anterior,
                'variacao_absoluta': variacao_absoluta,
                'variacao_percentual': variacao_percentual,
            }
        )
    return comparison
