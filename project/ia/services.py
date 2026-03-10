from __future__ import annotations

import json

import requests
from decouple import config

from .models import AnaliseConcorrencial


OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'


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


def build_report_payload(kpis, campaign_rows, comparison_rows, competitor_payload, competitor_analysis_text=''):
    top_competitors = competitor_payload.get('competitors', [])[:3]
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
                    'content': f'{prompt}\n\nDados estruturados:\n{json.dumps(payload, ensure_ascii=False)}',
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


def generate_competitor_analysis(competitor_payload):
    prompt = (
        'Analise apenas os dados observáveis/importados do concorrente informado e gere uma leitura subjetiva e estratégica. '
        'Estruture a resposta em 4 blocos curtos: 1) visão geral do movimento do concorrente, '
        '2) padrão de copy e oferta, 3) CTAs, posicionamento, presença no feed, constância de postagem e sinais de estratégia digital, '
        '4) oportunidades e alertas frente ao anunciante analisado. '
        'Nunca atribua métricas privadas reais aos concorrentes.'
    )
    return call_openrouter(prompt, {'concorrentes': competitor_payload})


def save_competitor_analysis(empresa, competitor_name, competitor_payload):
    analysis_text = generate_competitor_analysis(competitor_payload)
    AnaliseConcorrencial.objects.filter(empresa=empresa, concorrente_nome__iexact=competitor_name).delete()
    return AnaliseConcorrencial.objects.create(
        empresa=empresa,
        concorrente_nome=competitor_name,
        titulo=f'Análise do Concorrente - {competitor_name}',
        conteudo=analysis_text,
        total_anuncios=int(competitor_payload.get('total_anuncios') or 0),
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
        'Nos próximos passos econômicos, indique se faz sentido aumentar, reduzir ou redistribuir investimento e por quê. '
        'Nos próximos passos técnicos, recomende ajustes em campanha, público, criativos, segmentação e estrutura com objetividade. '
        'Nunca invente métricas privadas dos concorrentes. Se faltar base, diga isso explicitamente.'
    )
    return call_openrouter(prompt, report_payload)
