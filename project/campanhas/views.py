from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.utils import last_complete_month_ranges
from empresas.models import Empresa

from .forms import ComparePeriodForm, UploadCampanhaForm
from .models import UploadCampanha
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
    empresa_id = request.session.get('active_company_id')
    uploads = UploadCampanha.objects.select_related('empresa')
    if empresa_id:
        uploads = uploads.filter(empresa_id=empresa_id)
    return render(request, 'campanhas/upload_list.html', {'uploads': uploads})


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
        initial['empresa'] = empresa
    form = ComparePeriodForm(request.GET or None, initial=initial)
    queryset = metrics_queryset(
        empresa=empresa,
        data_inicio=default_ranges['current_start'],
        data_fim=default_ranges['current_end'],
    )
    previous_qs = metrics_queryset(
        empresa=empresa,
        data_inicio=default_ranges['previous_start'],
        data_fim=default_ranges['previous_end'],
    )

    if form.is_valid():
        empresa = form.cleaned_data.get('empresa') or empresa
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

    context = {
        'form': form,
        'empresa': empresa,
        'kpis': summarize_metrics(queryset),
        'campaign_rows': campaign_table(queryset),
        'campaign_comparison_rows': campaign_comparison_table(queryset, previous_qs),
        'stacked_campaign_charts': [
            stacked_campaign_comparison_chart(queryset, previous_qs, metric_key=metric_key)
            for metric_key in chart_metrics
        ],
        'comparison_rows': comparison_summary(queryset, previous_qs) if previous_qs.exists() else [],
    }
    return render(request, 'campanhas/dashboard.html', context)
