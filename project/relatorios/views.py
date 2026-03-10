from django.contrib import messages
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils.text import slugify

from campanhas.services import campaign_table, comparison_summary, metrics_queryset, stacked_campaign_comparison_chart, summarize_metrics
from concorrentes.models import ConcorrenteAd
from concorrentes.services import competitor_summary
from core.utils import last_complete_month_ranges
from empresas.models import Empresa
from ia.models import AnaliseConcorrencial
from ia.services import build_report_payload, generate_report_insights

from .models import Relatorio
from .services import render_pdf_bytes, render_report_html


def relatorio_list(request):
    relatorios = Relatorio.objects.select_related('empresa')
    company_id = request.session.get('active_company_id')
    if company_id:
        relatorios = relatorios.filter(empresa_id=company_id)
    return render(request, 'relatorios/list.html', {'relatorios': relatorios})


def relatorio_generate(request):
    if request.method != 'POST':
        messages.info(request, 'Gere o relatório a partir do dashboard para considerar os dados exibidos na tela.')
        return redirect('campanhas:dashboard')

    empresa = get_object_or_404(Empresa, pk=request.POST.get('empresa'))
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
    selected_competitor_name = request.POST.get('competitor_analysis', '')
    latest_competitor_analysis = (
        AnaliseConcorrencial.objects.filter(empresa=empresa, concorrente_nome=selected_competitor_name).first()
        if selected_competitor_name
        else AnaliseConcorrencial.objects.filter(empresa=empresa).exclude(concorrente_nome='').first()
    )

    report_payload = build_report_payload(
        kpis,
        campaign_rows,
        comparison_rows,
        competitor_payload,
        latest_competitor_analysis.conteudo if latest_competitor_analysis else '',
    )
    insight_text = generate_report_insights(report_payload)
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
        'selected_competitor_name': selected_competitor_name,
        'periodo_inicio': periodo_inicio,
        'periodo_fim': periodo_fim,
        'periodo_inicio_anterior': periodo_inicio_anterior,
        'periodo_fim_anterior': periodo_fim_anterior,
        'titulo': titulo,
        'report_charts': report_charts,
    }
    if competitor_payload.get('competitors') and selected_competitor_name:
        context['selected_competitor_profile'] = next(
            (
                item for item in competitor_payload['competitors']
                if item['nome'] == selected_competitor_name
            ),
            None,
        )
    else:
        context['selected_competitor_profile'] = None
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
