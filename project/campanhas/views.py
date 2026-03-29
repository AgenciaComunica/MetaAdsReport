from urllib.parse import urlencode

from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.utils import last_complete_month_ranges
from empresas.services import empresa_digital_summary
from empresas.models import Empresa
from concorrentes.models import ConcorrenteAd
from concorrentes.services import competitor_profiles, competitor_summary, competitor_summary_for_name_in_period
from ia.models import AnaliseConcorrencial
from relatorios.models import Relatorio

from .forms import ComparePeriodForm, UploadCampanhaForm
from .models import UploadCampanha
from .dashboard_upload_tabs import build_dashboard_upload_tabs
from .services import (
    campaign_comparison_table,
    COLUMN_ALIASES,
    campaign_table,
    comparison_summary,
    import_metrics_from_upload,
    metrics_queryset,
    stacked_campaign_comparison_chart,
    summarize_metrics,
    timeline_data,
)


def upload_list(request):
    query = {}
    empresa_id = request.GET.get('empresa') or request.session.get('active_company_id')
    if empresa_id:
        query['empresa'] = empresa_id
    query['tab'] = 'uploads'
    return redirect(f"{reverse('campanhas:dashboard')}?{urlencode(query)}")


def upload_create(request):
    empresa_inicial = None
    empresa_id = request.session.get('active_company_id')
    if empresa_id:
        empresa_inicial = Empresa.objects.filter(pk=empresa_id).first()
    form = UploadCampanhaForm(request.POST or None, request.FILES or None, empresa_inicial=empresa_inicial)
    if request.method == 'POST' and form.is_valid():
        upload = form.save()
        result = import_metrics_from_upload(upload)
        upload.colunas_mapeadas_json = result.mapping
        upload.observacoes_importacao = '\n'.join(result.warnings)
        upload.save(update_fields=['colunas_mapeadas_json', 'observacoes_importacao'])
        if result.missing_required:
            request.session['pending_upload_id'] = upload.pk
            messages.warning(request, 'A importação precisa de mapeamento manual para continuar.')
            return redirect('campanhas:manual_mapping', pk=upload.pk)
        messages.success(
            request,
            f'Upload importado com {result.imported_count} linhas. '
            f'Duplicadas no arquivo: {result.duplicate_in_file_count}. '
            f'Duplicadas de uploads anteriores: {result.duplicate_existing_count}.'
        )
        for warning in result.warnings:
            messages.warning(request, warning)
        return redirect('campanhas:upload_detail', pk=upload.pk)
    return render(request, 'campanhas/upload_form.html', {'form': form})


def manual_mapping(request, pk):
    upload = get_object_or_404(UploadCampanha, pk=pk)
    probe = import_metrics_from_upload(upload)

    class ManualMappingForm(forms.Form):
        pass

    choices = [('', '---')] + [(column, column) for column in probe.detected_columns]
    for field, label in [('campaign_name', 'Campanha'), ('date', 'Data'), ('amount_spent', 'Investimento'), ('impressions', 'Impressões'), ('reach', 'Alcance'), ('link_clicks', 'Cliques'), ('ctr', 'CTR'), ('cpc', 'CPC'), ('cpm', 'CPM'), ('results', 'Resultados')]:
        ManualMappingForm.base_fields[field] = forms.ChoiceField(
            choices=choices,
            required=field == 'campaign_name',
            label=label,
            initial=probe.mapping.get(field, ''),
            widget=forms.Select(attrs={'class': 'form-select'}),
        )

    form = ManualMappingForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        result = import_metrics_from_upload(upload, manual_mapping=form.cleaned_data)
        upload.colunas_mapeadas_json = result.mapping
        upload.observacoes_importacao = '\n'.join(result.warnings)
        upload.save(update_fields=['colunas_mapeadas_json', 'observacoes_importacao'])
        messages.success(
            request,
            f'Mapeamento aplicado. {result.imported_count} linhas importadas. '
            f'Duplicadas no arquivo: {result.duplicate_in_file_count}. '
            f'Duplicadas de uploads anteriores: {result.duplicate_existing_count}.'
        )
        for warning in result.warnings:
            messages.warning(request, warning)
        return redirect('campanhas:upload_detail', pk=upload.pk)

    alias_help = {key: ', '.join(values[:4]) for key, values in COLUMN_ALIASES.items()}
    return render(
        request,
        'campanhas/manual_mapping.html',
        {'upload': upload, 'form': form, 'detected_columns': probe.detected_columns, 'alias_help': alias_help},
    )


def upload_detail(request, pk):
    upload = get_object_or_404(UploadCampanha.objects.select_related('empresa'), pk=pk)
    queryset = upload.metricas.all()
    context = {
        'upload': upload,
        'kpis': summarize_metrics(queryset),
        'campaign_rows': campaign_table(queryset),
        'timeline': timeline_data(queryset),
    }
    return render(request, 'campanhas/upload_detail.html', context)


def upload_delete(request, pk):
    upload = get_object_or_404(UploadCampanha.objects.select_related('empresa'), pk=pk)
    if request.method == 'POST':
        nome_referencia = upload.nome_referencia
        upload.delete()
        messages.success(request, f'Upload "{nome_referencia}" removido com sucesso.')
        return redirect('campanhas:upload_list')
    return render(request, 'campanhas/upload_confirm_delete.html', {'upload': upload})


def upload_campaign_delete(request, pk):
    upload = get_object_or_404(UploadCampanha.objects.select_related('empresa'), pk=pk)
    campaign_name = request.POST.get('campaign_name') or request.GET.get('campaign')
    if not campaign_name:
        messages.error(request, 'Campanha não informada para exclusão.')
        return redirect('campanhas:upload_detail', pk=upload.pk)

    metrics_qs = upload.metricas.filter(campanha=campaign_name)
    if not metrics_qs.exists():
        messages.error(request, 'Campanha não encontrada neste upload.')
        return redirect('campanhas:upload_detail', pk=upload.pk)

    if request.method == 'POST':
        deleted_count, _ = metrics_qs.delete()
        messages.success(request, f'Campanha "{campaign_name}" removida do upload. {deleted_count} registro(s) excluído(s).')
        return redirect('campanhas:upload_detail', pk=upload.pk)

    return render(
        request,
        'campanhas/upload_campaign_confirm_delete.html',
        {
            'upload': upload,
            'campaign_name': campaign_name,
            'records_count': metrics_qs.count(),
        },
    )


def dashboard(request):
    dashboard_tab = request.GET.get('tab') or 'trafego_pago'
    allowed_tabs = {'trafego_pago', 'crm_vendas', 'analise_completa', 'uploads', 'concorrentes', 'relatorios'}
    if dashboard_tab not in allowed_tabs:
        dashboard_tab = 'trafego_pago'
    chart_metrics = ['resultados', 'investimento', 'impressoes', 'alcance', 'cliques', 'ctr', 'cpc', 'cpm', 'cpl']
    default_ranges = last_complete_month_ranges()
    initial = {
        'data_inicio': default_ranges['current_start'],
        'data_fim': default_ranges['current_end'],
        'data_inicio_anterior': default_ranges['previous_start'],
        'data_fim_anterior': default_ranges['previous_end'],
    }
    empresa = None
    company_id = request.session.get('active_company_id')
    if company_id:
        empresa = Empresa.objects.filter(pk=company_id).first()
    if empresa is None:
        empresa = Empresa.objects.order_by('nome', 'pk').first()
        if empresa:
            request.session['active_company_id'] = empresa.pk
    if empresa:
        initial['empresa'] = empresa
    form = ComparePeriodForm(request.GET or None, initial=initial)
    queryset = metrics_queryset(
        empresa=empresa,
        data_inicio=default_ranges['current_start'],
        data_fim=default_ranges['current_end'],
    )
    current_start = default_ranges['current_start']
    current_end = default_ranges['current_end']
    previous_start = default_ranges['previous_start']
    previous_end = default_ranges['previous_end']
    previous_qs = metrics_queryset(
        empresa=empresa,
        data_inicio=default_ranges['previous_start'],
        data_fim=default_ranges['previous_end'],
    )

    if form.is_valid():
        empresa = form.cleaned_data.get('empresa') or empresa
        if empresa:
            request.session['active_company_id'] = empresa.pk
        current_start = form.cleaned_data.get('data_inicio') or default_ranges['current_start']
        current_end = form.cleaned_data.get('data_fim') or default_ranges['current_end']
        previous_start = form.cleaned_data.get('data_inicio_anterior') or default_ranges['previous_start']
        previous_end = form.cleaned_data.get('data_fim_anterior') or default_ranges['previous_end']
        queryset = metrics_queryset(
            empresa=empresa,
            data_inicio=current_start,
            data_fim=current_end,
        )
        previous_qs = metrics_queryset(
            empresa=empresa,
            data_inicio=previous_start,
            data_fim=previous_end,
        )
    else:
        current_start = default_ranges['current_start']
        current_end = default_ranges['current_end']

    competitor_qs = ConcorrenteAd.objects.filter(empresa=empresa) if empresa else ConcorrenteAd.objects.none()
    competitor_analyses = (
        AnaliseConcorrencial.objects.filter(empresa=empresa).exclude(concorrente_nome='')
        if empresa
        else AnaliseConcorrencial.objects.none()
    )
    if empresa:
        competitor_analyses = competitor_analyses.filter(concorrente_nome__in=[name for name in competitor_qs.values_list('concorrente_nome', flat=True)])
    competitor_analysis_panels = []
    company_digital = empresa_digital_summary(empresa, current_start, current_end) if empresa and empresa.instagram_profile_url else None
    if empresa:
        for analysis in competitor_analyses:
            summary = competitor_summary_for_name_in_period(competitor_qs, analysis.concorrente_nome, current_start, current_end)
            profile = summary['competidor']
            if profile.get('activity_label') == 'Sem Avaliação Feita':
                profile['activity_label'] = 'Sem Ads'
            competitor_analysis_panels.append(
                {
                    'analysis': analysis,
                    'competidor': profile,
                    'feed_insights': summary['feed_insights'],
                }
            )
        competitor_analysis_panels.sort(
            key=lambda item: (
                -(item['feed_insights'].get('digital_score') or 0),
                item['analysis'].concorrente_nome.lower(),
            )
        )
    open_analysis = request.GET.get('open_analysis') or (competitor_analysis_panels[0]['analysis'].concorrente_nome if competitor_analysis_panels else '')
    overall_competitor_summary = (
        competitor_summary(ConcorrenteAd.objects.filter(empresa=empresa)) if empresa else {'competitors': []}
    )
    analysis_names = set(competitor_analyses.values_list('concorrente_nome', flat=True)) if empresa else set()
    for competitor in overall_competitor_summary.get('competitors', []):
        if competitor['nome'] in analysis_names and competitor.get('activity_label') == 'Sem Avaliação Feita':
            competitor['activity_label'] = 'Sem Ads'

    dashboard_upload_tabs = build_dashboard_upload_tabs(empresa, queryset, current_start, current_end) if empresa else []
    dashboard_upload_tab_map = {tab['key']: tab for tab in dashboard_upload_tabs}

    uploads_list = UploadCampanha.objects.select_related('empresa')
    uploads_list = uploads_list.filter(empresa=empresa) if empresa else uploads_list

    concorrentes_list_qs = ConcorrenteAd.objects.select_related('empresa').filter(categoria='Perfil importado')
    concorrentes_list_qs = concorrentes_list_qs.filter(empresa=empresa) if empresa else concorrentes_list_qs
    competitor_status_map = {item['nome']: item for item in competitor_profiles(concorrentes_list_qs)}
    analyses_map = {
        (analysis.empresa_id, analysis.concorrente_nome): analysis
        for analysis in AnaliseConcorrencial.objects.exclude(concorrente_nome='')
    }
    concorrentes_list = list(concorrentes_list_qs[:300])
    for ad in concorrentes_list:
        profile = competitor_status_map.get(ad.concorrente_nome.strip())
        ad.activity_label = profile['activity_label'] if profile else 'Sem Avaliação Feita'
        ad.activity_class = profile['activity_class'] if profile else 'is-none'
        ad.analysis = analyses_map.get((ad.empresa_id, ad.concorrente_nome))
        ad.has_analysis = ad.analysis is not None
        ad.open_analysis_url = (
            f"{reverse('campanhas:dashboard')}?{urlencode({'empresa': ad.empresa_id, 'tab': 'overview', 'open_analysis': ad.concorrente_nome})}#analise-digital"
            if ad.has_analysis
            else ''
        )
        if ad.has_analysis and ad.activity_label == 'Sem Avaliação Feita':
            ad.activity_label = 'Sem Ads'

    relatorios_list = Relatorio.objects.select_related('empresa')
    relatorios_list = relatorios_list.filter(empresa=empresa) if empresa else relatorios_list

    context = {
        'dashboard_tab': dashboard_tab,
        'form': form,
        'empresa': empresa,
        'periodo_atual_resumo': f'{current_start:%d-%m-%y} até {current_end:%d-%m-%y}',
        'periodo_anterior_resumo': f'{previous_start:%d-%m-%y} até {previous_end:%d-%m-%y}',
        'kpis': summarize_metrics(queryset),
        'campaign_rows': campaign_table(queryset),
        'campaign_comparison_rows': campaign_comparison_table(queryset, previous_qs),
        'stacked_campaign_charts': [
            stacked_campaign_comparison_chart(queryset, previous_qs, metric_key=metric_key)
            for metric_key in chart_metrics
        ],
        'comparison_rows': comparison_summary(queryset, previous_qs) if previous_qs.exists() else [],
        'company_digital': company_digital,
        'competitor_analyses': competitor_analyses,
        'competitor_analysis_panels': competitor_analysis_panels,
        'open_analysis': open_analysis,
        'competitor_summary': overall_competitor_summary,
        'dashboard_upload_tabs': dashboard_upload_tabs,
        'crm_vendas_tab': dashboard_upload_tab_map.get('crm_vendas'),
        'analise_completa_tab': dashboard_upload_tab_map.get('analise_completa'),
        'uploads_list': uploads_list,
        'concorrentes_list': concorrentes_list,
        'relatorios_list': relatorios_list,
    }
    return render(request, 'campanhas/dashboard.html', context)
