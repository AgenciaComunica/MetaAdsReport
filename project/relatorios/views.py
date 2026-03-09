from django.contrib import messages
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from campanhas.services import campaign_table, metrics_queryset, summarize_metrics, timeline_data
from concorrentes.models import ConcorrenteAd
from concorrentes.services import competitor_summary
from core.utils import last_complete_month_ranges
from ia.services import build_analysis_payload, generate_strategic_insights

from .forms import RelatorioGeracaoForm
from .models import Relatorio
from .services import render_pdf_bytes, render_report_html


def relatorio_list(request):
    relatorios = Relatorio.objects.select_related('empresa')
    company_id = request.session.get('active_company_id')
    if company_id:
        relatorios = relatorios.filter(empresa_id=company_id)
    return render(request, 'relatorios/list.html', {'relatorios': relatorios})


def relatorio_generate(request):
    form = RelatorioGeracaoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        empresa = form.cleaned_data['empresa']
        default_ranges = last_complete_month_ranges()
        periodo_inicio = form.cleaned_data['periodo_inicio'] or default_ranges['current_start']
        periodo_fim = form.cleaned_data['periodo_fim'] or default_ranges['current_end']
        queryset = metrics_queryset(empresa=empresa, data_inicio=periodo_inicio, data_fim=periodo_fim)
        competitor_qs = ConcorrenteAd.objects.filter(empresa=empresa)
        kpis = summarize_metrics(queryset)
        campaign_rows = campaign_table(queryset)
        my_payload = build_analysis_payload(kpis, campaign_rows)
        competitor_payload = competitor_summary(competitor_qs)
        insight_text = generate_strategic_insights(my_payload, competitor_payload)
        comparison_rows = []
        context = {
            'empresa': empresa,
            'kpis': kpis,
            'campaign_rows': campaign_rows,
            'timeline': timeline_data(queryset),
            'comparison_rows': comparison_rows,
            'competitor_summary': competitor_payload,
            'insight_text': insight_text,
            'periodo_inicio': periodo_inicio,
            'periodo_fim': periodo_fim,
            'titulo': form.cleaned_data['titulo'],
        }
        html = render_report_html(context)
        relatorio = Relatorio.objects.create(
            empresa=empresa,
            titulo=form.cleaned_data['titulo'],
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            tipo_periodo=form.cleaned_data['tipo_periodo'],
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
    return render(request, 'relatorios/form.html', {'form': form})


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
