from __future__ import annotations

import json

import pandas as pd

from .models import ConcorrenteAd


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
    return {
        'total_anuncios': queryset.count(),
        'ctas': ctas[:20],
        'categorias': categorias[:20],
        'amostras_texto': textos[:10],
        'amostras_titulo': titulos[:10],
        'observacao_limite': 'Analise baseada apenas em dados observáveis/importados, sem inferir métricas privadas dos concorrentes.',
    }

