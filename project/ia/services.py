from __future__ import annotations

import json

import requests
from decouple import config


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

