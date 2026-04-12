from urllib.parse import urlencode

from django.contrib import messages
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.text import slugify

from campanhas.services import campaign_table, comparison_summary, metrics_queryset, stacked_campaign_comparison_chart, summarize_metrics
from concorrentes.models import ConcorrenteAd
from concorrentes.services import competitor_summary, competitor_summary_for_name_in_period
from core.utils import last_complete_month_ranges
from empresas.models import Empresa
from empresas.services import empresa_digital_summary
from ia.models import AnaliseConcorrencial
from ia.services import build_report_payload, generate_report_insights, split_analysis_sections

from .models import Relatorio
from .services import render_pdf_bytes, render_report_html


def relatorio_list(request):
    return redirect(f"{reverse('campanhas:dashboard')}?tab=analise_completa")


def relatorio_generate(request):
    if request.method != 'POST':
        messages.info(request, 'Gere o relatório a partir do dashboard para considerar os dados exibidos na tela.')
        return redirect('campanhas:dashboard')

    empresa = Empresa.objects.order_by('pk').first()
    if not empresa:
        messages.error(request, 'Nenhuma empresa configurada.')
        return redirect('campanhas:dashboard')
    default_ranges = last_complete_month_ranges()
    periodo_inicio = parse_date(request.POST.get('data_inicio') or '') or default_ranges['current_start']
    periodo_fim = parse_date(request.POST.get('data_fim') or '') or default_ranges['current_end']
    periodo_inicio_anterior = parse_date(request.POST.get('data_inicio_anterior') or '') or default_ranges['previous_start']
    periodo_fim_anterior = parse_date(request.POST.get('data_fim_anterior') or '') or default_ranges['previous_end']

    queryset = metrics_queryset(empresa=empresa, data_inicio=periodo_inicio, data_fim=periodo_fim)
    previous_qs = metrics_queryset(empresa=empresa, data_inicio=periodo_inicio_anterior, data_fim=periodo_fim_anterior)
    competitor_qs = ConcorrenteAd.objects.filter(empresa=empresa)

    kpis = summarize_metrics(queryset)
    campaign_rows = campaign_table(queryset)
    comparison_rows = comparison_summary(queryset, previous_qs) if previous_qs.exists() else []
    competitor_payload = competitor_summary(competitor_qs)
    analysis_names = set(
        AnaliseConcorrencial.objects.filter(empresa=empresa).exclude(concorrente_nome='').values_list('concorrente_nome', flat=True)
    )
    for competitor in competitor_payload.get('competitors', []):
        if competitor['nome'] in analysis_names and competitor.get('activity_label') == 'Sem Avaliação Feita':
            competitor['activity_label'] = 'Sem Ads'
    competitor_analyses = list(
        AnaliseConcorrencial.objects.filter(
            empresa=empresa,
            concorrente_nome__in=competitor_qs.exclude(concorrente_nome='').values_list('concorrente_nome', flat=True),
        ).exclude(concorrente_nome='')
    )
    latest_competitor_analysis = competitor_analyses[0] if competitor_analyses else None
    company_digital = empresa_digital_summary(empresa, periodo_inicio, periodo_fim) if empresa.instagram_profile_url else None

    competitor_panels = []
    for analysis in competitor_analyses:
        competitor_item = competitor_summary_for_name_in_period(competitor_qs, analysis.concorrente_nome, periodo_inicio, periodo_fim)
        profile = competitor_item['competidor']
        if profile.get('activity_label') == 'Sem Avaliação Feita':
            profile['activity_label'] = 'Sem Ads'
        competitor_panels.append(
            {
                'analysis': analysis,
                'competidor': profile,
                'feed_insights': competitor_item['feed_insights'],
            }
        )
    competitor_panels.sort(key=lambda item: (-(item['feed_insights'].get('digital_score') or 0), item['analysis'].concorrente_nome.lower()))
    competitor_rankings = [
        {
            'nome': item['analysis'].concorrente_nome,
            'score_digital': int(item['feed_insights'].get('digital_score') or 0),
            'score_label': item['feed_insights'].get('digital_score_label') or '',
            'ads_ativos': int(item['competidor'].get('ads_biblioteca_sinal') or 0),
            'feed_no_periodo': int(item['feed_insights'].get('posts_visiveis_periodo') or 0),
            'interacoes_no_periodo': int(item['feed_insights'].get('interacoes_periodo') or 0),
            'status_ads': item['competidor'].get('activity_label') or '',
        }
        for item in competitor_panels
    ]
    report_payload = build_report_payload(
        kpis,
        campaign_rows,
        comparison_rows,
        competitor_payload,
        latest_competitor_analysis.conteudo if latest_competitor_analysis else '',
        company_digital=company_digital,
        competitor_rankings=competitor_rankings,
    )
    insight_text = generate_report_insights(report_payload)
    insight_sections = split_analysis_sections(insight_text)
    intro_titles = {'Resumo Executivo', 'Análise das Campanhas'}
    intro_sections = [section for section in insight_sections if section['title'] in intro_titles]
    conclusion_sections = [section for section in insight_sections if section['title'] not in intro_titles]
    titulo = request.POST.get('titulo') or f'Relatório {empresa.nome} {periodo_inicio:%m/%Y}'

    chart_metrics = ['resultados', 'investimento', 'impressoes', 'alcance', 'cliques', 'ctr', 'cpc', 'cpm', 'cpl']
    report_charts = []
    for metric_key in chart_metrics:
        chart = stacked_campaign_comparison_chart(queryset, previous_qs, metric_key=metric_key)
        report_charts.append(
            {
                **chart,
                'current_total': sum(item['data'][0] for item in chart['series']),
                'previous_total': sum(item['data'][1] for item in chart['series']),
            }
        )

    context = {
        'empresa': empresa,
        'kpis': kpis,
        'campaign_rows': campaign_rows,
        'comparison_rows': comparison_rows,
        'competitor_summary': competitor_payload,
        'insight_text': insight_text,
        'latest_competitor_analysis': latest_competitor_analysis,
        'periodo_inicio': periodo_inicio,
        'periodo_fim': periodo_fim,
        'periodo_inicio_anterior': periodo_inicio_anterior,
        'periodo_fim_anterior': periodo_fim_anterior,
        'titulo': titulo,
        'report_charts': report_charts,
        'intro_sections': intro_sections,
        'conclusion_sections': conclusion_sections,
    }
    context['company_digital'] = company_digital
    context['competitor_analysis_panels'] = competitor_panels
    html = render_report_html(context)
    relatorio = Relatorio.objects.create(
        empresa=empresa,
        titulo=titulo,
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        tipo_periodo=Relatorio.TipoPeriodo.PERSONALIZADO,
        resumo_ia=insight_text[:3000],
        insights_ia=insight_text,
        html_renderizado=html,
    )
    pdf_bytes = render_pdf_bytes(html, base_url=request.build_absolute_uri('/'))
    if pdf_bytes:
        filename = f"{slugify(relatorio.titulo)}.pdf"
        relatorio.pdf_arquivo.save(filename, ContentFile(pdf_bytes), save=True)
        messages.success(request, 'Relatório gerado com PDF.')
    else:
        messages.info(request, 'Relatório gerado em HTML. PDF indisponível neste ambiente.')
    return redirect('relatorios:detail', pk=relatorio.pk)


def relatorio_detail(request, pk):
    relatorio = get_object_or_404(Relatorio.objects.select_related('empresa'), pk=pk)
    return render(request, 'relatorios/detail.html', {'relatorio': relatorio})


def relatorio_html_export(request, pk):
    relatorio = get_object_or_404(Relatorio, pk=pk)
    return HttpResponse(relatorio.html_renderizado, content_type='text/html; charset=utf-8')


def relatorio_pdf_export(request, pk):
    relatorio = get_object_or_404(Relatorio, pk=pk)
    if not relatorio.pdf_arquivo:
        messages.error(request, 'PDF não disponível para este relatório.')
        return redirect('relatorios:detail', pk=pk)
    response = HttpResponse(relatorio.pdf_arquivo.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{slugify(relatorio.titulo)}.pdf"'
    return response


def relatorio_delete(request, pk):
    relatorio = get_object_or_404(Relatorio.objects.select_related('empresa'), pk=pk)
    if request.method == 'POST':
        titulo = relatorio.titulo
        if relatorio.pdf_arquivo:
            relatorio.pdf_arquivo.delete(save=False)
        relatorio.delete()
        messages.success(request, f'Relatório "{titulo}" removido com sucesso.')
        return redirect('relatorios:list')
    return render(request, 'relatorios/confirm_delete.html', {'relatorio': relatorio})
