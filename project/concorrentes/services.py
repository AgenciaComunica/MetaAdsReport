from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from html import unescape
from urllib.parse import quote, urlparse

import pandas as pd
import requests

from .models import ConcorrenteAd


ACTIVITY_META = {
    'alto': {'label': 'Alto Ads', 'class_name': 'is-high', 'color': '#b42318'},
    'medio': {'label': 'Médio Ads', 'class_name': 'is-medium', 'color': '#b54708'},
    'baixo': {'label': 'Baixo Ads', 'class_name': 'is-low', 'color': '#175cd3'},
    'sem': {'label': 'Sem Avaliação Feita', 'class_name': 'is-none', 'color': '#667085'},
}


def import_competitor_file(empresa, file_path):
    if file_path.lower().endswith('.json'):
        with open(file_path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        rows = data if isinstance(data, list) else data.get('items', [])
        df = pd.DataFrame(rows)
    else:
        df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8-sig')

    imported = 0
    for _, row in df.fillna('').iterrows():
        ConcorrenteAd.objects.create(
            empresa=empresa,
            concorrente_nome=str(row.get('concorrente_nome') or row.get('competitor') or row.get('advertiser') or 'Concorrente').strip(),
            texto_principal=str(row.get('texto_principal') or row.get('primary_text') or row.get('text') or ''),
            titulo=str(row.get('titulo') or row.get('title') or ''),
            descricao=str(row.get('descricao') or row.get('description') or ''),
            cta=str(row.get('cta') or row.get('call_to_action') or ''),
            plataforma=str(row.get('plataforma') or row.get('platform') or 'Meta Ads'),
            link=str(row.get('link') or row.get('url') or ''),
            categoria=str(row.get('categoria') or row.get('category') or ''),
            observacoes=str(row.get('observacoes') or row.get('notes') or ''),
        )
        imported += 1
    return imported


def competitor_summary(queryset):
    ctas = list(queryset.exclude(cta='').values_list('cta', flat=True))
    categorias = list(queryset.exclude(categoria='').values_list('categoria', flat=True))
    textos = [item for item in queryset.values_list('texto_principal', flat=True) if item]
    titulos = [item for item in queryset.values_list('titulo', flat=True) if item]
    competitors = competitor_profiles(queryset)
    return {
        'total_anuncios': queryset.count(),
        'ctas': ctas[:20],
        'categorias': categorias[:20],
        'amostras_texto': textos[:10],
        'amostras_titulo': titulos[:10],
        'competitors': competitors,
        'observacao_limite': 'Analise baseada apenas em dados observáveis/importados, sem inferir métricas privadas dos concorrentes.',
    }


def competitor_summary_for_name(queryset, competitor_name):
    competitor_queryset = queryset.filter(concorrente_nome__iexact=competitor_name)
    summary = competitor_summary(competitor_queryset)
    profile = next((item for item in summary['competitors'] if item['nome'].lower() == competitor_name.strip().lower()), None)
    summary['competidor'] = profile or {
        'nome': competitor_name,
        'activity_label': ACTIVITY_META['sem']['label'],
        'activity_class': ACTIVITY_META['sem']['class_name'],
        'real_ads_count': 0,
        'total_registros': 0,
        'feed_posts_visiveis': 0,
        'feed_cadencia': 'Base insuficiente para medir constância',
        'feed_datas_publicadas': [],
        'feed_formatos': {},
    }
    summary['feed_insights'] = {
        'posts_visiveis': summary['competidor'].get('feed_posts_visiveis', 0),
        'cadencia': summary['competidor'].get('feed_cadencia', ''),
        'datas_posts': summary['competidor'].get('feed_datas_publicadas', [])[:8],
        'formatos': summary['competidor'].get('feed_formatos', {}),
    }
    return summary


def classify_competitor_activity(real_ads_count):
    if real_ads_count >= 6:
        return ACTIVITY_META['alto']
    if real_ads_count >= 3:
        return ACTIVITY_META['medio']
    if real_ads_count >= 1:
        return ACTIVITY_META['baixo']
    return ACTIVITY_META['sem']


def competitor_profiles(queryset):
    grouped = defaultdict(lambda: {'total_registros': 0, 'real_ads_count': 0})
    for ad in queryset:
        name = (ad.concorrente_nome or 'Concorrente').strip()
        grouped[name]['total_registros'] += 1
        if (ad.categoria or '').strip().lower() != 'perfil importado':
            grouped[name]['real_ads_count'] += 1
        grouped[name].setdefault('feed_posts_visiveis', 0)
        grouped[name].setdefault('feed_cadencia', '')
        grouped[name].setdefault('feed_datas_publicadas', set())
        grouped[name].setdefault('feed_formatos', defaultdict(int))
        grouped[name]['feed_posts_visiveis'] = max(grouped[name]['feed_posts_visiveis'], ad.feed_posts_visiveis or 0)
        if ad.feed_cadencia:
            grouped[name]['feed_cadencia'] = ad.feed_cadencia
        for post_date in ad.feed_datas_publicadas or []:
            grouped[name]['feed_datas_publicadas'].add(post_date)
        for key, value in (ad.feed_formatos or {}).items():
            grouped[name]['feed_formatos'][key] += int(value or 0)

    profiles = []
    for name, values in grouped.items():
        activity = classify_competitor_activity(values['real_ads_count'])
        profiles.append(
            {
                'nome': name,
                'total_registros': values['total_registros'],
                'real_ads_count': values['real_ads_count'],
                'activity_label': activity['label'],
                'activity_class': activity['class_name'],
                'activity_color': activity['color'],
                'feed_posts_visiveis': values['feed_posts_visiveis'],
                'feed_cadencia': values['feed_cadencia'],
                'feed_datas_publicadas': sorted(values['feed_datas_publicadas'], reverse=True),
                'feed_formatos': dict(values['feed_formatos']),
            }
        )

    return sorted(profiles, key=lambda item: (-item['real_ads_count'], item['nome'].lower()))


def extract_instagram_username(profile_url):
    parsed = urlparse(profile_url)
    path_parts = [part for part in parsed.path.split('/') if part]
    if not path_parts:
        raise ValueError('Nao foi possivel identificar o usuario a partir da URL do Instagram.')
    return path_parts[0].strip('@')


def instagram_api_headers(profile_url):
    return {
        'User-Agent': (
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        ),
        'X-IG-App-ID': '936619743392459',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': profile_url,
    }


def build_meta_ad_library_url(keyword):
    encoded = quote(keyword)
    return (
        'https://www.facebook.com/ads/library/'
        f'?active_status=active&ad_type=all&country=ALL&is_targeted_country=false&media_type=all&q={encoded}&search_type=keyword_unordered'
    )


def fetch_instagram_profile_metadata(profile_url):
    response = requests.get(
        profile_url,
        headers=instagram_api_headers(profile_url),
        timeout=20,
    )
    response.raise_for_status()
    html = response.text

    def find_meta(property_name):
        patterns = [
            rf'<meta[^>]+property=["\']{property_name}["\'][^>]+content=["\'](.*?)["\']',
            rf'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']{property_name}["\']',
            rf'<meta[^>]+name=["\']{property_name}["\'][^>]+content=["\'](.*?)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return unescape(match.group(1)).strip()
        return ''

    title = find_meta('og:title')
    description = find_meta('og:description') or find_meta('description')
    return {
        'title': title,
        'description': description,
    }


def infer_posting_cadence(post_dates):
    if len(post_dates) < 2:
        return 'Base insuficiente para medir constância'
    parsed = [datetime.fromisoformat(value).date() for value in post_dates]
    gaps = [(parsed[index] - parsed[index + 1]).days for index in range(len(parsed) - 1)]
    average_gap = sum(gaps) / len(gaps)
    if average_gap <= 3:
        return 'Atualização muito constante'
    if average_gap <= 7:
        return 'Atualização constante'
    if average_gap <= 14:
        return 'Atualização moderada'
    return 'Atualização pontual'


def fetch_instagram_feed_insights(profile_url, username, count=12):
    response = requests.get(
        f'https://www.instagram.com/api/v1/feed/user/{username}/username/?count={count}',
        headers=instagram_api_headers(profile_url),
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    items = data.get('items', []) or []
    post_dates = []
    format_counts = defaultdict(int)

    for item in items:
        timestamp = item.get('taken_at')
        if timestamp:
            post_dates.append(datetime.fromtimestamp(timestamp).date().isoformat())
        product_type = item.get('product_type')
        media_type = item.get('media_type')
        if product_type == 'clips':
            format_counts['Reels'] += 1
        elif media_type == 8:
            format_counts['Carrossel'] += 1
        elif media_type == 1:
            format_counts['Imagem'] += 1
        elif media_type == 2:
            format_counts['Vídeo'] += 1

    return {
        'posts_visiveis': len(items),
        'datas_posts': post_dates,
        'cadencia': infer_posting_cadence(post_dates),
        'formatos': dict(format_counts),
    }


def import_instagram_profile(empresa, profile_url):
    username = extract_instagram_username(profile_url)
    ad_library_url = build_meta_ad_library_url(username)
    title = ''
    description = ''
    warnings = []
    feed_insights = {
        'posts_visiveis': 0,
        'datas_posts': [],
        'cadencia': 'Base insuficiente para medir constância',
        'formatos': {},
    }

    try:
        metadata = fetch_instagram_profile_metadata(profile_url)
        title = metadata.get('title', '')
        description = metadata.get('description', '')
    except Exception:
        warnings.append('Nao foi possivel ler metadados publicos do perfil. O cadastro foi feito com base apenas na URL.')

    try:
        feed_insights = fetch_instagram_feed_insights(profile_url, username)
    except Exception:
        warnings.append('Nao foi possivel capturar a timeline publica recente do feed neste momento.')

    nome_concorrente = title.split('•')[0].strip() if title else username
    observacoes = (
        f'Perfil importado por URL do Instagram.\n'
        f'Usuario detectado: @{username}\n'
        f'Consultar anuncios ativos na Meta Ad Library: {ad_library_url}\n'
        f'Posts visiveis captados no feed: {feed_insights["posts_visiveis"]}\n'
        f'Cadencia recente de postagem: {feed_insights["cadencia"]}\n'
        f'Datas recentes do feed: {", ".join(feed_insights["datas_posts"][:6]) or "-"}\n'
        f'Limitacao: a Meta nao oferece um fluxo publico estavel para capturar automaticamente anuncios comerciais gerais a partir do perfil.'
    )
    if warnings:
        observacoes += '\n' + '\n'.join(warnings)

    ad, _ = ConcorrenteAd.objects.update_or_create(
        empresa=empresa,
        concorrente_nome=nome_concorrente[:255],
        categoria='Perfil importado',
        defaults={
            'texto_principal': description[:5000],
            'titulo': title[:255],
            'descricao': description[:1000],
            'plataforma': 'Instagram / Meta Ads',
            'link': profile_url,
            'feed_posts_visiveis': feed_insights['posts_visiveis'],
            'feed_datas_publicadas': feed_insights['datas_posts'][:12],
            'feed_cadencia': feed_insights['cadencia'][:100],
            'feed_formatos': feed_insights['formatos'],
            'observacoes': observacoes,
        },
    )
    return ad, warnings
