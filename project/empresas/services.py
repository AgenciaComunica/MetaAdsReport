from __future__ import annotations

from django.utils import timezone

from concorrentes.services import (
    build_score_badge,
    build_meta_ad_library_url,
    fetch_instagram_feed_insights,
    fetch_instagram_profile_metadata,
    inspect_meta_ads_library,
    summarize_feed_activity,
    extract_instagram_username,
)

LEGACY_DIGITAL_NOTE_MARKERS = (
    'Instagram da empresa:',
    'Meta Ads Library:',
    'Busca usada:',
    'Ads ativos encontrados:',
)


def strip_empresa_legacy_digital_notes(text):
    raw_text = (text or '').strip()
    if not raw_text:
        return ''

    cleaned_lines = []
    for line in raw_text.splitlines():
        normalized = line.strip()
        if not normalized:
            if cleaned_lines and cleaned_lines[-1]:
                cleaned_lines.append('')
            continue
        if any(normalized.startswith(marker) for marker in LEGACY_DIGITAL_NOTE_MARKERS):
            continue
        cleaned_lines.append(line)

    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()
    return '\n'.join(cleaned_lines).strip()


def refresh_empresa_profile_record(empresa, ads_session=None):
    profile_url = empresa.instagram_profile_url
    if not profile_url:
        return empresa, ['A empresa não possui URL do Instagram cadastrada.']

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
    ads_library = {'query': '', 'signal': 0, 'active': False}

    try:
        metadata = fetch_instagram_profile_metadata(profile_url)
        title = metadata.get('title', '')
        description = metadata.get('description', '')
        followers_count = metadata.get('followers_count', 0)
        posts_count = metadata.get('posts_count', 0)
    except Exception:
        warnings.append('Nao foi possivel ler os metadados publicos do Instagram da empresa.')
        followers_count = 0
        posts_count = 0

    try:
        feed_insights = fetch_instagram_feed_insights(profile_url, username)
    except Exception:
        warnings.append('Nao foi possivel capturar a timeline publica recente do Instagram da empresa.')

    try:
        ads_library = inspect_meta_ads_library(empresa.nome, username, title.split('•')[0].strip() if title else '', session=ads_session)
    except Exception:
        warnings.append('Nao foi possivel consultar a Meta Ads Library da empresa neste momento.')

    empresa.ads_biblioteca_ativo = ads_library['active']
    empresa.ads_biblioteca_query = ads_library['query'][:255]
    empresa.ads_biblioteca_sinal = ads_library['signal']
    empresa.ads_biblioteca_consultado_em = timezone.now()
    empresa.seguidores = followers_count
    empresa.posts_total_publicos = posts_count
    empresa.feed_posts_visiveis = feed_insights['posts_visiveis']
    empresa.feed_posts_detalhes = feed_insights['posts_details']
    empresa.feed_datas_publicadas = feed_insights['datas_posts'][:12]
    empresa.feed_cadencia = feed_insights['cadencia'][:100]
    empresa.feed_formatos = feed_insights['formatos']

    empresa.observacoes = strip_empresa_legacy_digital_notes(empresa.observacoes)

    empresa.save(
        update_fields=[
            'observacoes',
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
        ]
    )
    return empresa, warnings


def empresa_digital_summary(empresa, period_start=None, period_end=None):
    feed_insights = summarize_feed_activity(
        empresa.feed_posts_detalhes or [],
        follower_count=empresa.seguidores or 0,
        real_ads_count=empresa.ads_biblioteca_sinal or 0,
        period_start=period_start,
        period_end=period_end,
    )
    score_badge = build_score_badge(feed_insights['digital_score'])
    return {
        'nome': empresa.nome,
        'instagram_profile_url': empresa.instagram_profile_url,
        'ads_biblioteca_ativo': empresa.ads_biblioteca_ativo,
        'ads_biblioteca_query': empresa.ads_biblioteca_query,
        'ads_biblioteca_sinal': empresa.ads_biblioteca_sinal,
        'ads_biblioteca_consultado_em': empresa.ads_biblioteca_consultado_em,
        'seguidores': empresa.seguidores,
        'posts_total_publicos': empresa.posts_total_publicos,
        'feed_posts_visiveis': empresa.feed_posts_visiveis,
        'feed_cadencia': empresa.feed_cadencia,
        'feed_formatos': empresa.feed_formatos or {},
        'feed_insights': feed_insights,
        'digital_score_label': score_badge['label'],
        'digital_score_class': score_badge['class_name'],
    }
