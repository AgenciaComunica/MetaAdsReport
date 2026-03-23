from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime
from html import unescape
from urllib.parse import quote, urlparse

import pandas as pd
import requests
from django.utils import timezone

from .models import ConcorrenteAd


ACTIVITY_META = {
    'alto': {'label': 'Alto Ads', 'class_name': 'is-high', 'color': '#b42318'},
    'medio': {'label': 'Médio Ads', 'class_name': 'is-medium', 'color': '#b54708'},
    'baixo': {'label': 'Baixo Ads', 'class_name': 'is-low', 'color': '#175cd3'},
    'sem': {'label': 'Sem Avaliação Feita', 'class_name': 'is-none', 'color': '#667085'},
}

UPDATE_META = {
    'always': {'label': 'Perfil Sempre Atualizado', 'class_name': 'is-high'},
    'very': {'label': 'Perfil Muito Atualizado', 'class_name': 'is-warm'},
    'updated': {'label': 'Perfil Atualizado', 'class_name': 'is-low'},
    'little': {'label': 'Perfil Pouco Atualizado', 'class_name': 'is-fresh'},
    'none': {'label': 'Perfil sem atualização', 'class_name': 'is-none'},
}

ADS_LIBRARY_HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept-Language': 'pt-BR,pt;q=0.9',
}
ADS_LIBRARY_BASE_URL = 'https://www.facebook.com/ads/library/'
ADS_LIBRARY_COUNT_RE = re.compile(r'"search_results_connection":\{"count":(\d+),"edges":')
ADS_LIBRARY_VERIFY_RE = re.compile(r"fetch\('([^']*__rd_verify[^']*)'")
ADS_LIBRARY_SUFFIXES = (
    'sports',
    'sport',
    'esportes',
    'esporte',
    'store',
    'oficial',
    'ofc',
    'shop',
)


def build_score_badge(score):
    if score >= 8:
        return {'label': f'Score Digital: {score}', 'class_name': 'is-high'}
    if score >= 4:
        return {'label': f'Score Digital: {score}', 'class_name': 'is-warm'}
    return {'label': f'Score Digital: {score}', 'class_name': 'is-fresh'}


def facebook_ads_library_session():
    session = requests.Session()
    session.headers.update(ADS_LIBRARY_HEADERS)
    return session


def ensure_ads_library_access(session):
    response = session.get(ADS_LIBRARY_BASE_URL, timeout=30)
    if response.status_code != 403:
        return
    match = ADS_LIBRARY_VERIFY_RE.search(response.text)
    if not match:
        response.raise_for_status()
    verify_url = f'https://www.facebook.com{match.group(1)}'
    verify_response = session.post(
        verify_url,
        headers={**ADS_LIBRARY_HEADERS, 'Referer': ADS_LIBRARY_BASE_URL},
        timeout=30,
    )
    verify_response.raise_for_status()


def normalize_ads_query_candidate(value):
    candidate = re.sub(r'https?://(www\.)?instagram\.com/', '', value or '', flags=re.IGNORECASE)
    candidate = candidate.split('?')[0].strip().strip('/').strip('@')
    candidate = re.sub(r'[_\-.]+', ' ', candidate)
    candidate = re.sub(r'\s+', ' ', candidate).strip()
    return candidate


def split_ads_library_suffixes(value):
    compact = re.sub(r'[^a-z0-9]', '', (value or '').lower())
    variants = []
    for suffix in ADS_LIBRARY_SUFFIXES:
        if compact.endswith(suffix) and len(compact) > len(suffix) + 2:
            prefix = compact[: -len(suffix)]
            variants.append(f'{prefix} {suffix}')
    return variants


def ads_library_query_candidates(*values):
    candidates = []
    seen = set()
    for value in values:
        if not value:
            continue
        raw = normalize_ads_query_candidate(value)
        for option in filter(None, [raw, raw.replace('  ', ' '), *split_ads_library_suffixes(raw)]):
            normalized = re.sub(r'\s+', ' ', option).strip()
            key = normalized.lower()
            if len(normalized) < 3 or key in seen:
                continue
            seen.add(key)
            candidates.append(normalized)
    return candidates


def fetch_meta_ads_library_count(keyword, session=None):
    if not keyword:
        return 0
    session = session or facebook_ads_library_session()
    ensure_ads_library_access(session)
    response = session.get(
        (
            f'{ADS_LIBRARY_BASE_URL}?active_status=active&ad_type=all&country=ALL'
            f'&is_targeted_country=false&media_type=all&search_type=keyword_unordered'
            f'&q={quote(keyword)}&_fb_noscript=1'
        ),
        headers={**ADS_LIBRARY_HEADERS, 'Referer': ADS_LIBRARY_BASE_URL},
        timeout=30,
    )
    response.raise_for_status()
    matches = ADS_LIBRARY_COUNT_RE.findall(response.text)
    return max((int(match) for match in matches), default=0)


def inspect_meta_ads_library(*query_candidates, session=None):
    session = session or facebook_ads_library_session()
    best_query = ''
    best_signal = 0
    for candidate in ads_library_query_candidates(*query_candidates):
        try:
            signal = fetch_meta_ads_library_count(candidate, session=session)
        except Exception:
            continue
        if signal > best_signal:
            best_signal = signal
            best_query = candidate
    return {
        'query': best_query,
        'signal': best_signal,
        'active': best_signal > 0,
    }


def ads_library_signal_to_count(signal):
    if signal >= 12:
        return 6
    if signal >= 4:
        return 3
    if signal >= 1:
        return 1
    return 0


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
    return competitor_summary_for_name_in_period(queryset, competitor_name)


def competitor_summary_for_name_in_period(queryset, competitor_name, period_start=None, period_end=None):
    competitor_queryset = queryset.filter(concorrente_nome__iexact=competitor_name)
    summary = competitor_summary(competitor_queryset)
    profile = next((item for item in summary['competitors'] if item['nome'].lower() == competitor_name.strip().lower()), None)
    summary['competidor'] = profile or {
        'nome': competitor_name,
        'activity_label': ACTIVITY_META['sem']['label'],
        'activity_class': ACTIVITY_META['sem']['class_name'],
        'real_ads_count': 0,
        'total_registros': 0,
        'seguidores': 0,
        'posts_total_publicos': 0,
        'feed_posts_visiveis': 0,
        'feed_posts_detalhes': [],
        'feed_cadencia': 'Base insuficiente para medir constância',
        'feed_datas_publicadas': [],
        'feed_formatos': {},
        'ads_biblioteca_ativo': False,
        'ads_biblioteca_query': '',
        'ads_biblioteca_sinal': 0,
        'ads_biblioteca_consultado_em': None,
    }
    summary['feed_insights'] = summarize_feed_activity(
        summary['competidor'].get('feed_posts_detalhes', []),
        follower_count=summary['competidor'].get('seguidores', 0),
        real_ads_count=summary['competidor'].get('real_ads_count', 0),
        period_start=period_start,
        period_end=period_end,
    )
    summary['feed_insights']['cadencia_total'] = summary['competidor'].get('feed_cadencia', '')
    summary['feed_insights']['posts_total_publicos'] = summary['competidor'].get('posts_total_publicos', 0)
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
        grouped[name].setdefault('seguidores', 0)
        grouped[name].setdefault('posts_total_publicos', 0)
        grouped[name].setdefault('feed_posts_visiveis', 0)
        grouped[name].setdefault('feed_posts_detalhes', [])
        grouped[name].setdefault('feed_cadencia', '')
        grouped[name].setdefault('feed_datas_publicadas', set())
        grouped[name].setdefault('feed_formatos', defaultdict(int))
        grouped[name].setdefault('ads_biblioteca_ativo', False)
        grouped[name].setdefault('ads_biblioteca_query', '')
        grouped[name].setdefault('ads_biblioteca_sinal', 0)
        grouped[name].setdefault('ads_biblioteca_consultado_em', None)
        grouped[name]['seguidores'] = max(grouped[name]['seguidores'], ad.seguidores or 0)
        grouped[name]['posts_total_publicos'] = max(grouped[name]['posts_total_publicos'], ad.posts_total_publicos or 0)
        grouped[name]['feed_posts_visiveis'] = max(grouped[name]['feed_posts_visiveis'], ad.feed_posts_visiveis or 0)
        grouped[name]['ads_biblioteca_ativo'] = grouped[name]['ads_biblioteca_ativo'] or bool(ad.ads_biblioteca_ativo)
        if (ad.ads_biblioteca_sinal or 0) >= grouped[name]['ads_biblioteca_sinal']:
            grouped[name]['ads_biblioteca_sinal'] = ad.ads_biblioteca_sinal or 0
            grouped[name]['ads_biblioteca_query'] = ad.ads_biblioteca_query or grouped[name]['ads_biblioteca_query']
            grouped[name]['ads_biblioteca_consultado_em'] = ad.ads_biblioteca_consultado_em
        if ad.feed_posts_detalhes:
            grouped[name]['feed_posts_detalhes'] = ad.feed_posts_detalhes
        if ad.feed_cadencia:
            grouped[name]['feed_cadencia'] = ad.feed_cadencia
        for post_date in ad.feed_datas_publicadas or []:
            grouped[name]['feed_datas_publicadas'].add(post_date)
        for key, value in (ad.feed_formatos or {}).items():
            grouped[name]['feed_formatos'][key] += int(value or 0)

    profiles = []
    for name, values in grouped.items():
        effective_ads_count = max(values['real_ads_count'], ads_library_signal_to_count(values['ads_biblioteca_sinal']))
        activity = classify_competitor_activity(effective_ads_count)
        profiles.append(
            {
                'nome': name,
                'total_registros': values['total_registros'],
                'real_ads_count': effective_ads_count,
                'ads_observados_count': values['real_ads_count'],
                'activity_label': activity['label'],
                'activity_class': activity['class_name'],
                'activity_color': activity['color'],
                'seguidores': values['seguidores'],
                'posts_total_publicos': values['posts_total_publicos'],
                'feed_posts_visiveis': values['feed_posts_visiveis'],
                'feed_posts_detalhes': values['feed_posts_detalhes'],
                'feed_cadencia': values['feed_cadencia'],
                'feed_datas_publicadas': sorted(values['feed_datas_publicadas'], reverse=True),
                'feed_formatos': dict(values['feed_formatos']),
                'ads_biblioteca_ativo': values['ads_biblioteca_ativo'],
                'ads_biblioteca_query': values['ads_biblioteca_query'],
                'ads_biblioteca_sinal': values['ads_biblioteca_sinal'],
                'ads_biblioteca_consultado_em': values['ads_biblioteca_consultado_em'],
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
    followers_count, following_count, posts_count = parse_instagram_counts(description)
    return {
        'title': title,
        'description': description,
        'followers_count': followers_count,
        'following_count': following_count,
        'posts_count': posts_count,
    }


def parse_instagram_counts(description):
    if not description:
        return 0, 0, 0
    match = re.search(
        r'([\d,\.]+)\s+Followers,\s+([\d,\.]+)\s+Following,\s+([\d,\.]+)\s+Posts',
        description,
        re.IGNORECASE,
    )
    if not match:
        return 0, 0, 0

    def parse_count(value):
        return int(re.sub(r'[^0-9]', '', value) or 0)

    return parse_count(match.group(1)), parse_count(match.group(2)), parse_count(match.group(3))


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


def fetch_instagram_feed_insights(profile_url, username, count=50):
    headers = instagram_api_headers(profile_url)
    items = []
    next_max_id = None
    while len(items) < count:
        page_size = min(12, count - len(items))
        url = f'https://www.instagram.com/api/v1/feed/user/{username}/username/?count={page_size}'
        if next_max_id:
            url = f'{url}&max_id={quote(str(next_max_id))}'
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        page_items = data.get('items', []) or []
        if not page_items:
            break
        items.extend(page_items)
        if not data.get('more_available') or not data.get('next_max_id'):
            break
        next_max_id = data.get('next_max_id')
    post_dates = []
    format_counts = defaultdict(int)
    posts_details = []

    for item in items:
        timestamp = item.get('taken_at')
        if timestamp:
            post_date = datetime.fromtimestamp(timestamp).date().isoformat()
            post_dates.append(post_date)
        else:
            post_date = None
        product_type = item.get('product_type')
        media_type = item.get('media_type')
        if product_type == 'clips':
            format_label = 'Reels'
        elif media_type == 8:
            format_label = 'Carrossel'
        elif media_type == 1:
            format_label = 'Imagem'
        elif media_type == 2:
            format_label = 'Vídeo'
        else:
            format_label = 'Outro'
        format_counts[format_label] += 1
        posts_details.append(
            {
                'date': post_date,
                'like_count': int(item.get('like_count') or 0),
                'comment_count': int(item.get('comment_count') or 0),
                'interaction_count': int(item.get('like_count') or 0) + int(item.get('comment_count') or 0),
                'format': format_label,
            }
        )

    posts_details.sort(key=lambda item: item.get('date') or '', reverse=True)
    post_dates = [item['date'] for item in posts_details if item.get('date')]

    return {
        'posts_visiveis': len(posts_details),
        'datas_posts': post_dates,
        'cadencia': infer_posting_cadence(post_dates),
        'formatos': dict(format_counts),
        'posts_details': posts_details,
    }


def summarize_feed_activity(posts_details, follower_count=0, real_ads_count=0, period_start=None, period_end=None):
    filtered = []
    for item in posts_details or []:
        if not item.get('date'):
            continue
        post_date = date.fromisoformat(item['date'])
        if period_start and post_date < period_start:
            continue
        if period_end and post_date > period_end:
            continue
        filtered.append(item)

    total_posts = len(filtered)
    total_likes = sum(int(item.get('like_count') or 0) for item in filtered)
    total_comments = sum(int(item.get('comment_count') or 0) for item in filtered)
    total_interactions = total_likes + total_comments
    average_engagement_per_post = (total_interactions / total_posts) if total_posts else None
    engagement_rate = None
    if follower_count and total_posts:
        engagement_rate = (total_interactions / (follower_count * total_posts)) * 100
    update_status = classify_update_rate(total_posts, period_start, period_end)
    digital_score = calculate_digital_score(real_ads_count, total_posts, average_engagement_per_post or 0)
    score_badge = build_score_badge(digital_score)

    return {
        'posts_visiveis_periodo': total_posts,
        'likes_periodo': total_likes,
        'comments_periodo': total_comments,
        'interacoes_periodo': total_interactions,
        'media_engajamento_por_post': average_engagement_per_post,
        'engajamento_observavel_percentual': engagement_rate,
        'datas_posts': [item['date'] for item in filtered[:8]],
        'formatos_periodo': dict(_count_formats(filtered)),
        'taxa_atualizacao_label': update_status['label'],
        'taxa_atualizacao_class': update_status['class_name'],
        'digital_score': digital_score,
        'digital_score_label': score_badge['label'],
        'digital_score_class': score_badge['class_name'],
    }


def _count_formats(posts_details):
    grouped = defaultdict(int)
    for item in posts_details:
        grouped[item.get('format') or 'Outro'] += 1
    return grouped


def classify_update_rate(total_posts, period_start=None, period_end=None):
    if total_posts <= 0:
        return UPDATE_META['none']

    total_days = ((period_end - period_start).days + 1) if period_start and period_end else 30
    days_per_post = total_days / total_posts if total_posts else total_days

    if days_per_post <= 2:
        return UPDATE_META['always']
    if days_per_post <= 5:
        return UPDATE_META['very']
    if days_per_post <= 15:
        return UPDATE_META['updated']
    if days_per_post <= 30:
        return UPDATE_META['little']
    return UPDATE_META['none']


def calculate_digital_score(real_ads_count, total_posts, average_engagement_per_post):
    ads_points = 0
    if real_ads_count >= 6:
        ads_points = 4
    elif real_ads_count >= 3:
        ads_points = 3
    elif real_ads_count >= 1:
        ads_points = 2

    post_points = 0
    if total_posts >= 28:
        post_points = 3
    elif total_posts > 12:
        post_points = 2
    elif total_posts > 4:
        post_points = 1.5
    elif total_posts > 1:
        post_points = 1

    engagement_points = 0
    if average_engagement_per_post >= 150:
        engagement_points = 3
    elif average_engagement_per_post >= 60:
        engagement_points = 2
    elif average_engagement_per_post > 0:
        engagement_points = 1

    score = round(ads_points + post_points + engagement_points)
    return max(1, min(10, score))


def import_instagram_profile(empresa, profile_url):
    username = extract_instagram_username(profile_url)
    ad, _ = ConcorrenteAd.objects.update_or_create(
        empresa=empresa,
        concorrente_nome=username[:255],
        categoria='Perfil importado',
        defaults={
            'plataforma': 'Instagram / Meta Ads',
            'link': profile_url,
        },
    )
    return refresh_instagram_profile_record(ad)


def refresh_instagram_profile_record(ad, ads_session=None):
    profile_url = ad.link
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
        'posts_details': [],
    }
    ads_library = {
        'query': '',
        'signal': 0,
        'active': False,
    }

    try:
        metadata = fetch_instagram_profile_metadata(profile_url)
        title = metadata.get('title', '')
        description = metadata.get('description', '')
        followers_count = metadata.get('followers_count', 0)
        posts_count = metadata.get('posts_count', 0)
    except Exception:
        warnings.append('Nao foi possivel ler metadados publicos do perfil. O cadastro foi mantido com base apenas na URL.')
        followers_count = 0
        posts_count = 0

    try:
        feed_insights = fetch_instagram_feed_insights(profile_url, username)
    except Exception:
        warnings.append('Nao foi possivel capturar a timeline publica recente do feed neste momento.')

    try:
        ads_library = inspect_meta_ads_library(
            username,
            ad.concorrente_nome,
            title.split('•')[0].strip() if title else '',
            session=ads_session,
        )
    except Exception:
        warnings.append('Nao foi possivel consultar a Meta Ads Library neste momento.')

    nome_concorrente = title.split('•')[0].strip() if title else ad.concorrente_nome or username
    ads_status = 'Sim' if ads_library['active'] else 'Nao'
    observacoes = (
        f'Perfil importado por URL do Instagram.\n'
        f'Usuario detectado: @{username}\n'
        f'Seguidores visiveis: {followers_count}\n'
        f'Total de posts publicos informado pelo perfil: {posts_count}\n'
        f'Consulta da Meta Ads Library: {ad_library_url}\n'
        f'Busca usada na Meta Ads Library: {ads_library["query"] or "-"}\n'
        f'Anuncios ativos encontrados na Meta Ads Library: {ads_library["signal"]}\n'
        f'Tem sinal de trafego pago ativo: {ads_status}\n'
        f'Posts visiveis captados no feed: {feed_insights["posts_visiveis"]}\n'
        f'Cadencia recente de postagem: {feed_insights["cadencia"]}\n'
        f'Datas recentes do feed: {", ".join(feed_insights["datas_posts"][:6]) or "-"}\n'
        f'Limitacao: a leitura de ads depende da disponibilidade publica da Meta Ads Library no momento da consulta.'
    )
    if warnings:
        observacoes += '\n' + '\n'.join(warnings)

    ad.concorrente_nome = nome_concorrente[:255]
    ad.texto_principal = description[:5000]
    ad.titulo = title[:255]
    ad.descricao = description[:1000]
    ad.plataforma = 'Instagram / Meta Ads'
    ad.ads_biblioteca_ativo = ads_library['active']
    ad.ads_biblioteca_query = ads_library['query'][:255]
    ad.ads_biblioteca_sinal = ads_library['signal']
    ad.ads_biblioteca_consultado_em = timezone.now()
    ad.seguidores = followers_count
    ad.posts_total_publicos = posts_count
    ad.feed_posts_visiveis = feed_insights['posts_visiveis']
    ad.feed_posts_detalhes = feed_insights['posts_details']
    ad.feed_datas_publicadas = feed_insights['datas_posts'][:12]
    ad.feed_cadencia = feed_insights['cadencia'][:100]
    ad.feed_formatos = feed_insights['formatos']
    ad.observacoes = observacoes
    ad.save(
        update_fields=[
            'concorrente_nome',
            'texto_principal',
            'titulo',
            'descricao',
            'plataforma',
            'ads_biblioteca_ativo',
            'ads_biblioteca_query',
            'ads_biblioteca_sinal',
            'ads_biblioteca_consultado_em',
            'seguidores',
            'posts_total_publicos',
            'feed_posts_visiveis',
            'feed_posts_detalhes',
            'feed_datas_publicadas',
            'feed_cadencia',
            'feed_formatos',
            'observacoes',
        ]
    )
    return ad, warnings
