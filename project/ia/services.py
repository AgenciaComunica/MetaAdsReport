from __future__ import annotations

import json
import re
from datetime import date, datetime

import requests
from decouple import config

from .models import AnaliseConcorrencial


OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'


def split_analysis_sections(text):
    if not text:
        return []

    sections = []
    current_title = None
    current_lines = []

    for line in str(text).splitlines():
        heading_match = re.match(r'^###\s*(.+?)\s*$', line.strip())
        if heading_match:
            if current_title is not None:
                sections.append(
                    {
                        'title': current_title,
                        'content': '\n'.join(current_lines).strip(),
                    }
                )
            current_title = heading_match.group(1).strip()
            current_lines = []
            continue
        current_lines.append(line)

    if current_title is not None:
        sections.append(
            {
                'title': current_title,
                'content': '\n'.join(current_lines).strip(),
            }
        )

    if not sections and str(text).strip():
        sections.append({'title': '', 'content': str(text).strip()})
    return sections


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def build_analysis_payload(kpis, campaign_rows):
    return {
        'kpis': {
            'investimento': float(kpis.get('investimento') or 0),
            'impressoes': int(kpis.get('impressoes') or 0),
            'alcance': int(kpis.get('alcance') or 0),
            'cliques': int(kpis.get('cliques') or 0),
            'resultados': float(kpis.get('resultados') or 0),
            'ctr': float(kpis.get('ctr') or 0),
            'cpc': float(kpis.get('cpc') or 0),
            'cpm': float(kpis.get('cpm') or 0),
            'cpl': float(kpis.get('cpl') or 0),
        },
        'campanhas': [
            {
                'campanha': row['campanha'],
                'investimento': float(row['investimento']),
                'cliques': int(row['cliques']),
                'ctr': float(row['ctr']),
                'cpc': float(row['cpc']),
                'cpm': float(row['cpm']),
                'resultados': float(row['resultados']),
                'cpl': float(row['cpl']),
            }
            for row in campaign_rows[:12]
        ],
    }


def build_report_payload(kpis, campaign_rows, comparison_rows, competitor_payload, competitor_analysis_text='', company_digital=None, competitor_rankings=None):
    top_competitors = (competitor_rankings or competitor_payload.get('competitors', []))[:3]
    payload = {
        'kpis': {
            'investimento': float(kpis.get('investimento') or 0),
            'impressoes': int(kpis.get('impressoes') or 0),
            'alcance': int(kpis.get('alcance') or 0),
            'cliques': int(kpis.get('cliques') or 0),
            'resultados': float(kpis.get('resultados') or 0),
            'ctr': float(kpis.get('ctr') or 0),
            'cpc': float(kpis.get('cpc') or 0),
            'cpm': float(kpis.get('cpm') or 0),
            'cpl': float(kpis.get('cpl') or 0),
        },
        'campanhas': [
            {
                'campanha': row['campanha'],
                'investimento': float(row['investimento']),
                'impressoes': int(row['impressoes']),
                'alcance': int(row['alcance']),
                'cliques': int(row['cliques']),
                'ctr': float(row['ctr']),
                'cpc': float(row['cpc']),
                'cpm': float(row['cpm']),
                'resultados': float(row['resultados']),
                'cpl': float(row['cpl']),
            }
            for row in campaign_rows[:10]
        ],
        'comparativo': [
            {
                'metrica': row['label'],
                'atual': float(row['atual']),
                'anterior': float(row['anterior']),
                'variacao_absoluta': float(row['variacao_absoluta']),
                'variacao_percentual': float(row['variacao_percentual']) if row['variacao_percentual'] is not None else None,
            }
            for row in comparison_rows
        ],
        'concorrentes': {
            'total_anuncios': int(competitor_payload.get('total_anuncios') or 0),
            'top_ameacas': top_competitors,
            'ctas': competitor_payload.get('ctas', [])[:12],
            'categorias': competitor_payload.get('categorias', [])[:12],
            'analise_concorrencial_salva': competitor_analysis_text,
        },
    }
    if company_digital:
        payload['empresa_digital'] = company_digital
    return payload


def build_competitor_analysis_payload(competitor_payload, company_payload=None):
    competitor = competitor_payload.get('competidor') or {}
    feed = competitor_payload.get('feed_insights') or {}
    payload = {
        'concorrente': {
            'nome': competitor.get('nome', ''),
            'status_ads': competitor.get('activity_label', ''),
            'ads_meta_ads_library': {
                'ativos_encontrados': int(competitor.get('ads_biblioteca_sinal') or 0),
                'busca_utilizada': competitor.get('ads_biblioteca_query') or '',
                'consultado_em': competitor.get('ads_biblioteca_consultado_em'),
            },
            'periodo_analisado': {
                'feed_no_periodo': int(feed.get('posts_visiveis_periodo') or 0),
                'interacoes_no_periodo': int(feed.get('interacoes_periodo') or 0),
                'comentarios_no_periodo': int(feed.get('comments_periodo') or 0),
                'media_engajamento_por_post': float(feed.get('media_engajamento_por_post') or 0),
                'taxa_atualizacao': feed.get('taxa_atualizacao_label') or '',
                'formatos_no_periodo': feed.get('formatos_periodo') or {},
            },
        }
    }
    if company_payload:
        company_feed = company_payload.get('feed_insights') or {}
        payload['empresa_digital'] = {
            'nome': company_payload.get('nome', ''),
            'ads_meta_ads_library': {
                'ativos_encontrados': int(company_payload.get('ads_biblioteca_sinal') or 0),
                'busca_utilizada': company_payload.get('ads_biblioteca_query') or '',
            },
            'periodo_analisado': {
                'feed_no_periodo': int(company_feed.get('posts_visiveis_periodo') or 0),
                'interacoes_no_periodo': int(company_feed.get('interacoes_periodo') or 0),
                'comentarios_no_periodo': int(company_feed.get('comments_periodo') or 0),
                'media_engajamento_por_post': float(company_feed.get('media_engajamento_por_post') or 0),
                'taxa_atualizacao': company_feed.get('taxa_atualizacao_label') or '',
            },
        }
    return payload


def call_openrouter(prompt, payload):
    api_key = config('OPENROUTER_API_KEY', default='')
    model = config('OPENROUTER_MODEL', default='openai/gpt-4o-mini')
    if not api_key:
        return 'OPENROUTER_API_KEY não configurada. A análise de IA foi pulada.'

    response = requests.post(
        OPENROUTER_URL,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        json={
            'model': model,
            'messages': [
                {
                    'role': 'system',
                    'content': (
                        'Responda em português do Brasil, com linguagem profissional, sem inventar dados. '
                        'Se a base for limitada, diga isso explicitamente.'
                    ),
                },
                {
                    'role': 'user',
                    'content': f'{prompt}\n\nDados estruturados:\n{json.dumps(json_safe(payload), ensure_ascii=False)}',
                },
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data['choices'][0]['message']['content']


def generate_strategic_insights(my_data_payload, competitor_payload):
    prompt = (
        'Gere três blocos: 1) resumo executivo dos meus dados, 2) leitura dos concorrentes, '
        '3) comparativo estratégico com hipóteses e testes recomendados para o próximo período. '
        'Nunca atribua métricas privadas reais aos concorrentes.'
    )
    return call_openrouter(
        prompt,
        {'meus_dados': my_data_payload, 'concorrentes': competitor_payload},
    )


def generate_competitor_analysis(competitor_payload, company_payload=None):
    compact_payload = build_competitor_analysis_payload(competitor_payload, company_payload=company_payload)
    concorrente = compact_payload.get('concorrente', {})
    periodo = concorrente.get('periodo_analisado', {})
    ads = concorrente.get('ads_meta_ads_library', {})
    fatos_obrigatorios = (
        'FATOS OBRIGATÓRIOS PARA USAR NO TEXTO:\n'
        f'- Feed no período: {periodo.get("feed_no_periodo", 0)}\n'
        f'- Interações no período: {periodo.get("interacoes_no_periodo", 0)}\n'
        f'- Comentários no período: {periodo.get("comentarios_no_periodo", 0)}\n'
        f'- Média de engajamento por post: {periodo.get("media_engajamento_por_post", 0)}\n'
        f'- Taxa de atualização: {periodo.get("taxa_atualizacao", "")}\n'
        f'- Ads ativos na Meta Ads Library: {ads.get("ativos_encontrados", 0)}\n'
        'Esses números são a verdade do recorte. Não substitua, não reconte e não arredonde para outro total.\n'
    )
    prompt = (
        'Analise apenas os dados observáveis/importados do concorrente informado, respeitando o recorte de período enviado, e gere uma leitura subjetiva e estratégica. '
        'Use como fonte principal os campos do período em feed_insights, especialmente posts_visiveis_periodo, interacoes_periodo, comments_periodo, '
        'media_engajamento_por_post e taxa_atualizacao_label. '
        'Se houver dados da empresa analisada em empresa_digital, compare explicitamente o concorrente com a empresa em termos de constância, presença no feed, engajamento observável e sinal de ads ativos. '
        'Aponte onde o concorrente está acima, empatado ou abaixo da empresa, sem inventar dados. '
        'Considere como valor oficial do recorte apenas concorrente.periodo_analisado.feed_no_periodo. '
        'Nunca cite contagens, interações ou comentários que não estejam explicitamente dentro de concorrente.periodo_analisado. '
        'Se for mencionar feed, interações, comentários ou média por post, use exatamente os números presentes em concorrente.periodo_analisado. '
        'Se concorrente.ads_meta_ads_library.ativos_encontrados for maior que zero, trate isso como evidência pública de anúncios ativos na Meta Ads Library e cite isso com objetividade. '
        'Se concorrente.ads_meta_ads_library.ativos_encontrados for zero, diga que nao houve sinal público de ads ativos na Meta Ads Library no momento da consulta. '
        'Repita taxa_atualizacao exatamente como veio em concorrente.periodo_analisado.taxa_atualizacao. '
        'Se houver 4 posts ou menos no período, nao descreva a presença como forte, notável, robusta ou dominante; trate como presença limitada ou moderada. '
        'Se o concorrente nao tiver anuncios ativos observáveis nem sinal público de ads ativos na Meta Ads Library, diga isso claramente e evite superestimar sua pressão competitiva. '
        'Se a média de engajamento por post for moderada, use linguagem contida, sem adjetivos otimistas demais. '
        'Estruture a resposta em 4 blocos curtos: 1) visão geral do movimento do concorrente, '
        '2) padrão de copy e oferta, 3) CTAs, posicionamento, presença no feed, constância de postagem e engajamento observável no período, '
        '4) oportunidades e alertas frente ao anunciante analisado. '
        'No bloco 4, fale do risco e da pressão competitiva que o concorrente representa para a empresa analisada. '
        'Nao escreva recomendações para o concorrente nem diga o que o concorrente deveria fazer para melhorar. '
        'Escreva o bloco 4 do ponto de vista da empresa analisada: onde ela está exposta, onde está protegida e o que merece monitoramento imediato. '
        'Nunca atribua métricas privadas reais aos concorrentes.'
    )
    return call_openrouter(f'{fatos_obrigatorios}\n{prompt}', compact_payload)


def save_competitor_analysis(empresa, competitor_name, competitor_payload, company_payload=None):
    analysis_text = generate_competitor_analysis(competitor_payload, company_payload=company_payload)
    competitor = competitor_payload.get('competidor') or {}
    total_ads = max(
        int(competitor_payload.get('total_anuncios') or 0),
        int(competitor.get('ads_biblioteca_sinal') or 0),
        int(competitor.get('real_ads_count') or 0),
    )
    AnaliseConcorrencial.objects.filter(empresa=empresa, concorrente_nome__iexact=competitor_name).delete()
    return AnaliseConcorrencial.objects.create(
        empresa=empresa,
        concorrente_nome=competitor_name,
        titulo=f'Análise do Concorrente - {competitor_name}',
        conteudo=analysis_text,
        total_anuncios=total_ads,
    )


def generate_report_insights(report_payload):
    prompt = (
        'Gere um texto em português do Brasil com os títulos exatamente nesta ordem: '
        '### Resumo Executivo, '
        '### Análise das Campanhas, '
        '### Visão Geral dos Concorrentes, '
        '### Próximos Passos Econômicos, '
        '### Próximos Passos Técnicos. '
        'No resumo executivo, faça uma leitura breve do período. '
        'Na análise das campanhas, seja curta e objetiva com base nos resultados e no comparativo. '
        'Na visão geral dos concorrentes, classifique no máximo 3 concorrentes como maior ameaça, cite seus nomes e explique o que parecem estar fazendo como estratégia de ads digital com base apenas em dados observáveis/importados. '
        'Considere que concorrentes.top_ameacas já vem ordenado do maior Score Digital para o menor, e use essa ordem como ranking de risco para a empresa. '
        'Nos próximos passos econômicos, indique se faz sentido aumentar, reduzir ou redistribuir investimento e por quê. '
        'Nos próximos passos técnicos, traga apenas o ponto técnico mais importante e específico que está destoando no período. '
        'Esse bloco deve ter no máximo 2 frases curtas e não deve virar lista. '
        'Não sugira ajustes genéricos como público, segmentação, criativos, estrutura ou testes A/B se os dados não mostrarem claramente esse problema. '
        'Se não houver um desvio técnico claro nas campanhas, escreva exatamente: Sem pontos técnicos de melhoria na campanha. '
        'Nunca invente métricas privadas dos concorrentes. Se faltar base, diga isso explicitamente.'
    )
    return call_openrouter(prompt, report_payload)
