from urllib.parse import urlencode

from django import forms
from django.contrib import messages
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.utils import last_complete_month_ranges
from empresas.services import empresa_digital_summary
from empresas.models import ConfiguracaoUploadEmpresa, Empresa
from empresas.upload_config_services import inspect_uploaded_file, read_uploaded_dataframe
from concorrentes.models import ConcorrenteAd
from concorrentes.services import competitor_profiles, competitor_summary, competitor_summary_for_name_in_period
from ia.models import AnaliseConcorrencial
from relatorios.models import Relatorio

from .forms import ComparePeriodForm, EventoPainelForm, EventoPainelImportForm, UploadCampanhaForm, UploadPainelArquivoForm
from .models import EventoPainel, UploadCampanha, UploadPainel
from .dashboard_upload_tabs import build_dashboard_upload_tabs
from .services import (
    COLUMN_ALIASES,
    campaign_table,
    infer_upload_period_from_dataframe,
    import_metrics_from_upload,
    metrics_queryset,
    summarize_metrics,
    timeline_data,
)


def upload_list(request):
    query = {}
    empresa_id = request.GET.get('empresa') or request.session.get('active_company_id')
    if empresa_id:
        query['empresa'] = empresa_id
    return redirect(f"{reverse('campanhas:dashboard')}?{urlencode(query)}")


def upload_create(request):
    if request.method != 'POST':
        return redirect('campanhas:dashboard')
    empresa_inicial = None
    empresa_id = request.session.get('active_company_id')
    if empresa_id:
        empresa_inicial = Empresa.objects.filter(pk=empresa_id).first()
    form = UploadCampanhaForm(request.POST or None, request.FILES or None, empresa_inicial=empresa_inicial)
    if request.method == 'POST' and form.is_valid():
        upload = form.save(commit=False)
        traffic_config = (
            ConfiguracaoUploadEmpresa.objects.filter(
                empresa=upload.empresa,
                tipo_documento=ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO,
            )
            .order_by('pk')
            .first()
        )
        dataframe = read_uploaded_dataframe(upload.arquivo, upload.arquivo.name)
        data_inicio, data_fim, periodo_tipo = infer_upload_period_from_dataframe(
            dataframe,
            config_mapping=(traffic_config.mapeamento_json if traffic_config else {}),
        )
        upload.data_inicio = data_inicio
        upload.data_fim = data_fim
        upload.periodo_tipo = periodo_tipo
        upload.save()
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


def panel_upload_delete(request, pk):
    upload = get_object_or_404(UploadPainel.objects.select_related('configuracao__empresa'), pk=pk)
    empresa = upload.configuracao.empresa
    panel_key = request.GET.get('tab') or f'{upload.configuracao.tipo_documento}_{upload.configuracao.pk}'
    if request.method == 'POST':
        configuracao = upload.configuracao
        was_current = configuracao.nome_arquivo_exemplo == upload.nome_arquivo
        if upload.arquivo:
            upload.arquivo.delete(save=False)
        upload.delete()
        if was_current:
            latest_upload = configuracao.uploads_painel.order_by('-criado_em', '-pk').first()
            if latest_upload:
                configuracao.arquivo_exemplo = latest_upload.arquivo.name
                configuracao.nome_arquivo_exemplo = latest_upload.nome_arquivo
                configuracao.colunas_detectadas_json = latest_upload.colunas_detectadas_json
                configuracao.preview_json = latest_upload.preview_json
            else:
                configuracao.arquivo_exemplo = ''
                configuracao.nome_arquivo_exemplo = ''
                configuracao.colunas_detectadas_json = []
                configuracao.preview_json = []
            configuracao.save(update_fields=['arquivo_exemplo', 'nome_arquivo_exemplo', 'colunas_detectadas_json', 'preview_json'])
        messages.success(request, 'Upload removido com sucesso.')
    return redirect(f"{reverse('campanhas:dashboard')}?{urlencode({'empresa': empresa.pk, 'tab': panel_key})}")


def dashboard(request):
    dashboard_tab = request.GET.get('tab') or ''
    default_ranges = last_complete_month_ranges()
    initial = {
        'data_inicio': default_ranges['current_start'],
        'data_fim': default_ranges['current_end'],
        'data_inicio_anterior': default_ranges['previous_start'],
        'data_fim_anterior': default_ranges['previous_end'],
    }
    empresa_prefetch = Prefetch(
        'configuracoes_upload',
        queryset=ConfiguracaoUploadEmpresa.objects.exclude(tipo_documento='').prefetch_related('uploads_painel').order_by('nome', 'pk'),
    )
    empresa = None
    company_id = request.session.get('active_company_id')
    if company_id:
        empresa = Empresa.objects.prefetch_related(empresa_prefetch).filter(pk=company_id).first()
    if empresa is None:
        empresa = Empresa.objects.prefetch_related(empresa_prefetch).order_by('nome', 'pk').first()
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
            empresa = Empresa.objects.prefetch_related(empresa_prefetch).filter(pk=empresa.pk).first()
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

    show_upload_modal_key = ''
    traffic_upload_form = UploadCampanhaForm(prefix='upload-trafego', empresa_inicial=empresa)
    painel_upload_forms = {}
    evento_painel_forms = {}
    evento_import_forms = {}

    dashboard_upload_tabs = (
        build_dashboard_upload_tabs(
            empresa,
            queryset,
            current_start,
            current_end,
            previous_start=previous_start,
            previous_end=previous_end,
            previous_queryset=previous_qs,
            active_key=None,
        )
        if empresa
        else []
    )
    dashboard_upload_tab_map = {tab['key']: tab for tab in dashboard_upload_tabs}
    visible_dashboard_tabs = list(dashboard_upload_tabs)
    if empresa:
        analise_index = next(
            (index for index, item in enumerate(visible_dashboard_tabs) if item['key'] == 'analise_completa'),
            len(visible_dashboard_tabs),
        )
        insert_index = analise_index + 1 if analise_index < len(visible_dashboard_tabs) else len(visible_dashboard_tabs)
        visible_dashboard_tabs.insert(insert_index, {'key': 'concorrentes', 'title': 'Concorrentes'})
    visible_keys = {item['key'] for item in visible_dashboard_tabs}
    if dashboard_tab not in visible_keys and visible_dashboard_tabs:
        dashboard_tab = visible_dashboard_tabs[0]['key']
    elif dashboard_tab not in visible_keys:
        dashboard_tab = 'concorrentes'
    dashboard_upload_tabs = (
        build_dashboard_upload_tabs(
            empresa,
            queryset,
            current_start,
            current_end,
            previous_start=previous_start,
            previous_end=previous_end,
            previous_queryset=previous_qs,
            active_key=dashboard_tab,
        )
        if empresa
        else []
    )
    dashboard_upload_tab_map = {tab['key']: tab for tab in dashboard_upload_tabs}
    active_upload_tab = dashboard_upload_tab_map.get(dashboard_tab)
    if active_upload_tab and active_upload_tab.get('config_id') and active_upload_tab.get('panel_type') != ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO:
        configuracao = next(
            (item for item in empresa.configuracoes_upload.all() if item.pk == active_upload_tab['config_id']),
            None,
        ) if empresa else None
        if configuracao:
            if active_upload_tab.get('panel_type') == ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS:
                evento_painel_forms[active_upload_tab['key']] = EventoPainelForm(prefix=f'evento-{active_upload_tab["key"]}')
                evento_import_forms[active_upload_tab['key']] = EventoPainelImportForm(prefix=f'evento-import-{active_upload_tab["key"]}')
            else:
                painel_upload_forms[active_upload_tab['key']] = UploadPainelArquivoForm(
                    prefix=f'upload-{active_upload_tab["key"]}',
                    configuracao=configuracao,
                )

    competitor_qs = ConcorrenteAd.objects.filter(empresa=empresa) if empresa else ConcorrenteAd.objects.none()
    competitor_analyses = AnaliseConcorrencial.objects.none()
    competitor_analysis_panels = []
    company_digital = None
    open_analysis = request.GET.get('open_analysis') or ''
    overall_competitor_summary = {'competitors': []}
    if empresa and dashboard_tab == 'concorrentes':
        competitor_analyses = AnaliseConcorrencial.objects.filter(empresa=empresa).exclude(concorrente_nome='')
        competitor_analyses = competitor_analyses.filter(
            concorrente_nome__in=[name for name in competitor_qs.values_list('concorrente_nome', flat=True)]
        )
        company_digital = empresa_digital_summary(empresa, current_start, current_end) if empresa.instagram_profile_url else None
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
        open_analysis = open_analysis or (competitor_analysis_panels[0]['analysis'].concorrente_nome if competitor_analysis_panels else '')
        overall_competitor_summary = competitor_summary(competitor_qs)
        analysis_names = set(competitor_analyses.values_list('concorrente_nome', flat=True))
        for competitor in overall_competitor_summary.get('competitors', []):
            if competitor['nome'] in analysis_names and competitor.get('activity_label') == 'Sem Avaliação Feita':
                competitor['activity_label'] = 'Sem Ads'

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'novo_upload_trafego' and active_upload_tab and active_upload_tab.get('panel_type') == ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO:
            traffic_upload_form = UploadCampanhaForm(
                request.POST,
                request.FILES,
                prefix='upload-trafego',
                empresa_inicial=empresa,
            )
            if traffic_upload_form.is_valid():
                upload = traffic_upload_form.save(commit=False)
                traffic_config = None
                if active_upload_tab.get('config_id'):
                    traffic_config = next(
                        (item for item in empresa.configuracoes_upload.all() if item.pk == active_upload_tab['config_id']),
                        None,
                    ) if empresa else None
                dataframe = read_uploaded_dataframe(upload.arquivo, upload.arquivo.name)
                data_inicio, data_fim, periodo_tipo = infer_upload_period_from_dataframe(
                    dataframe,
                    config_mapping=(traffic_config.mapeamento_json if traffic_config else {}),
                )
                upload.data_inicio = data_inicio
                upload.data_fim = data_fim
                upload.periodo_tipo = periodo_tipo
                upload.save()
                result = import_metrics_from_upload(upload)
                upload.colunas_mapeadas_json = result.mapping
                upload.observacoes_importacao = '\n'.join(result.warnings)
                upload.save(update_fields=['colunas_mapeadas_json', 'observacoes_importacao'])
                if result.missing_required:
                    request.session['pending_upload_id'] = upload.pk
                    messages.warning(request, 'A importação precisa de mapeamento manual para continuar.')
                    return redirect('campanhas:manual_mapping', pk=upload.pk)
                messages.success(request, f'Upload importado com {result.imported_count} linhas.')
                return redirect(f"{reverse('campanhas:dashboard')}?{urlencode({'empresa': empresa.pk, 'tab': active_upload_tab['key']})}")
            show_upload_modal_key = active_upload_tab['key']
        elif action == 'novo_upload_painel':
            panel_key = request.POST.get('panel_key', '')
            panel_tab = dashboard_upload_tab_map.get(panel_key)
            if panel_tab and panel_tab.get('config_id'):
                configuracao = get_object_or_404(
                    ConfiguracaoUploadEmpresa.objects.select_related('empresa'),
                    pk=panel_tab['config_id'],
                    empresa=empresa,
                )
                form_key = panel_tab['key']
                painel_form = UploadPainelArquivoForm(
                    request.POST,
                    request.FILES,
                    prefix=f'upload-{form_key}',
                    configuracao=configuracao,
                )
                painel_upload_forms[form_key] = painel_form
                if painel_form.is_valid():
                    uploaded_file = painel_form.cleaned_data['arquivo']
                    tipo_upload = painel_form.cleaned_data.get('tipo_upload', '')
                    if not tipo_upload and configuracao.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS:
                        digital_type = str((configuracao.configuracao_analise_json or {}).get('digital_type', 'instagram')).strip()
                        if digital_type != 'instagram':
                            tipo_upload = 'principal'
                    preview = inspect_uploaded_file(uploaded_file, uploaded_file.name)
                    panel_upload = UploadPainel.objects.create(
                        configuracao=configuracao,
                        arquivo=uploaded_file,
                        tipo_upload=tipo_upload,
                        nome_arquivo=preview.file_name,
                        colunas_detectadas_json=preview.columns,
                        preview_json=preview.rows,
                    )
                    configuracao.arquivo_exemplo = panel_upload.arquivo.name
                    configuracao.nome_arquivo_exemplo = preview.file_name
                    configuracao.colunas_detectadas_json = preview.columns
                    configuracao.preview_json = preview.rows
                    configuracao.save(update_fields=['arquivo_exemplo', 'nome_arquivo_exemplo', 'colunas_detectadas_json', 'preview_json'])
                    messages.success(request, f'Arquivo enviado para o painel "{configuracao.nome}".')
                    return redirect(f"{reverse('campanhas:dashboard')}?{urlencode({'empresa': empresa.pk, 'tab': form_key})}")
                show_upload_modal_key = form_key
        elif action == 'novo_dado_evento':
            panel_key = request.POST.get('panel_key', '')
            panel_tab = dashboard_upload_tab_map.get(panel_key)
            if panel_tab and panel_tab.get('config_id') and panel_tab.get('panel_type') == ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS:
                configuracao = get_object_or_404(
                    ConfiguracaoUploadEmpresa.objects.select_related('empresa'),
                    pk=panel_tab['config_id'],
                    empresa=empresa,
                )
                evento_form = EventoPainelForm(request.POST, prefix=f'evento-{panel_key}')
                evento_painel_forms[panel_key] = evento_form
                if evento_form.is_valid():
                    evento = evento_form.save(commit=False)
                    evento.configuracao = configuracao
                    evento.save()
                    messages.success(request, f'Dado adicionado ao painel "{configuracao.nome}".')
                    return redirect(f"{reverse('campanhas:dashboard')}?{urlencode({'empresa': empresa.pk, 'tab': panel_key})}")
                show_upload_modal_key = panel_key
        elif action == 'importar_dados_evento':
            panel_key = request.POST.get('panel_key', '')
            panel_tab = dashboard_upload_tab_map.get(panel_key)
            if panel_tab and panel_tab.get('config_id') and panel_tab.get('panel_type') == ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS:
                configuracao = get_object_or_404(
                    ConfiguracaoUploadEmpresa.objects.select_related('empresa'),
                    pk=panel_tab['config_id'],
                    empresa=empresa,
                )
                import_form = EventoPainelImportForm(request.POST, request.FILES, prefix=f'evento-import-{panel_key}')
                evento_import_forms[panel_key] = import_form
                if import_form.is_valid():
                    imported_count = _import_eventos_painel_file(configuracao, import_form.cleaned_data['arquivo'])
                    messages.success(request, f'{imported_count} evento(s) importado(s) para o painel "{configuracao.nome}".')
                    return redirect(f"{reverse('campanhas:dashboard')}?{urlencode({'empresa': empresa.pk, 'tab': panel_key})}")
                show_upload_modal_key = panel_key

    uploads_list = UploadCampanha.objects.none()
    if active_upload_tab and active_upload_tab.get('panel_type') == ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO:
        uploads_list = UploadCampanha.objects.select_related('empresa')
        uploads_list = uploads_list.filter(empresa=empresa) if empresa else uploads_list

    concorrentes_list = []
    if dashboard_tab == 'concorrentes':
        concorrentes_list_qs = ConcorrenteAd.objects.select_related('empresa').filter(categoria='Perfil importado')
        concorrentes_list_qs = concorrentes_list_qs.filter(empresa=empresa) if empresa else concorrentes_list_qs
        competitor_status_map = {item['nome']: item for item in competitor_profiles(concorrentes_list_qs)}
        competitor_score_map = {}
        analyses_map = {
            (analysis.empresa_id, analysis.concorrente_nome): analysis
            for analysis in AnaliseConcorrencial.objects.filter(empresa=empresa).exclude(concorrente_nome='')
        }
        concorrentes_list = list(concorrentes_list_qs[:300])
        for ad in concorrentes_list:
            competitor_name = ad.concorrente_nome.strip()
            profile = competitor_status_map.get(competitor_name)
            ad.activity_label = profile['activity_label'] if profile else 'Sem Avaliação Feita'
            ad.activity_class = profile['activity_class'] if profile else 'is-none'
            ad.analysis = analyses_map.get((ad.empresa_id, ad.concorrente_nome))
            ad.has_analysis = ad.analysis is not None
            if competitor_name not in competitor_score_map:
                summary = competitor_summary_for_name_in_period(concorrentes_list_qs, competitor_name, current_start, current_end)
                competitor_score_map[competitor_name] = {
                    'score': int(summary['feed_insights'].get('digital_score') or 0),
                    'score_label': summary['feed_insights'].get('digital_score_label') or 'Score Digital: 0',
                    'score_class': summary['feed_insights'].get('digital_score_class') or 'is-fresh',
                }
            score_data = competitor_score_map[competitor_name]
            ad.score_digital = score_data['score']
            ad.score_digital_label = score_data['score_label']
            ad.score_digital_class = score_data['score_class']
            ad.open_analysis_url = (
                f"{reverse('campanhas:dashboard')}?{urlencode({'empresa': ad.empresa_id, 'tab': 'concorrentes', 'open_analysis': ad.concorrente_nome})}#analise-digital"
                if ad.has_analysis
                else ''
            )
            if ad.has_analysis and ad.activity_label == 'Sem Avaliação Feita':
                ad.activity_label = 'Sem Ads'

    relatorios_list = Relatorio.objects.none()
    if dashboard_tab == 'analise_completa':
        relatorios_list = Relatorio.objects.select_related('empresa')
        relatorios_list = relatorios_list.filter(empresa=empresa) if empresa else relatorios_list
    panel_uploads_list = (
        UploadPainel.objects.filter(configuracao_id=active_upload_tab.get('config_id')).select_related('configuracao')
        if active_upload_tab and active_upload_tab.get('config_id')
        else UploadPainel.objects.none()
    )
    eventos_painel_list = (
        EventoPainel.objects.filter(configuracao_id=active_upload_tab.get('config_id')).select_related('configuracao')
        if active_upload_tab and active_upload_tab.get('panel_type') == ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS and active_upload_tab.get('config_id')
        else EventoPainel.objects.none()
    )

    context = {
        'dashboard_tab': dashboard_tab,
        'form': form,
        'empresa': empresa,
        'periodo_atual_resumo': f'{current_start:%d-%m-%y} até {current_end:%d-%m-%y}',
        'periodo_anterior_resumo': f'{previous_start:%d-%m-%y} até {previous_end:%d-%m-%y}',
        'campaign_rows': campaign_table(queryset),
        'company_digital': company_digital,
        'competitor_analyses': competitor_analyses,
        'competitor_analysis_panels': competitor_analysis_panels,
        'open_analysis': open_analysis,
        'competitor_summary': overall_competitor_summary,
        'dashboard_upload_tabs': dashboard_upload_tabs,
        'visible_dashboard_tabs': visible_dashboard_tabs,
        'show_upload_modal_key': show_upload_modal_key,
        'traffic_upload_form': traffic_upload_form,
        'painel_upload_forms': painel_upload_forms,
        'evento_painel_forms': evento_painel_forms,
        'evento_import_forms': evento_import_forms,
        'active_upload_tab': active_upload_tab,
        'analise_completa_tab': dashboard_upload_tab_map.get('analise_completa'),
        'uploads_list': uploads_list,
        'panel_uploads_list': panel_uploads_list,
        'eventos_painel_list': eventos_painel_list,
        'concorrentes_list': concorrentes_list,
        'relatorios_list': relatorios_list,
    }
    return render(request, 'campanhas/dashboard.html', context)


def evento_painel_delete(request, pk):
    evento = get_object_or_404(EventoPainel.objects.select_related('configuracao__empresa'), pk=pk)
    empresa = evento.configuracao.empresa
    panel_key = request.GET.get('tab') or f'{evento.configuracao.tipo_documento}_{evento.configuracao.pk}'
    if request.method == 'POST':
        evento.delete()
        messages.success(request, 'Dado do painel removido com sucesso.')
    return redirect(f"{reverse('campanhas:dashboard')}?{urlencode({'empresa': empresa.pk, 'tab': panel_key})}")


def evento_painel_template_download(request):
    try:
        from openpyxl import Workbook
    except Exception:
        messages.error(request, 'Não foi possível gerar o template Excel neste ambiente.')
        return redirect('campanhas:dashboard')

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Eventos'
    headers = ['Nome do Evento', 'Data do Evento', 'Impacto', 'Pessoas Alcançadas']
    examples = [
        ['Feira Futsal', '2026-03-15', 'alto', 120],
        ['Ação no Clube', '2026-03-22', 'medio', 80],
    ]
    sheet.append(headers)
    for row in examples:
        sheet.append(row)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="template_presenca_fisica.xlsx"'
    workbook.save(response)
    return response


def _import_eventos_painel_file(configuracao, uploaded_file):
    dataframe = read_uploaded_dataframe(uploaded_file, uploaded_file.name)
    header_aliases = {
        'nome do evento': 'nome_evento',
        'evento': 'nome_evento',
        'data do evento': 'data_evento',
        'data': 'data_evento',
        'impacto': 'impacto',
        'acao': 'impacto',
        'ação': 'impacto',
        'pessoas alcançadas': 'leads_media',
        'pessoas alcancadas': 'leads_media',
        'leads alcançados em media': 'leads_media',
        'leads alcancados em media': 'leads_media',
        'leads_media': 'leads_media',
    }
    normalized_columns = {}
    for column in dataframe.columns:
        normalized = str(column).strip().lower()
        normalized_columns[column] = header_aliases.get(normalized, normalized)

    imported_count = 0
    for _, source_row in dataframe.iterrows():
        mapped = {}
        for original_column, target_field in normalized_columns.items():
            mapped[target_field] = source_row.get(original_column, '')
        nome_evento = str(mapped.get('nome_evento', '')).strip()
        if not nome_evento:
            continue
        impacto = str(mapped.get('impacto', '')).strip().lower() or EventoPainel.ImpactoChoices.MEDIO
        if impacto not in {choice for choice, _ in EventoPainel.ImpactoChoices.choices}:
            impacto = EventoPainel.ImpactoChoices.MEDIO
        EventoPainel.objects.create(
            configuracao=configuracao,
            nome_evento=nome_evento,
            data_evento=mapped.get('data_evento'),
            impacto=impacto,
            leads_media=int(mapped.get('leads_media') or 0),
        )
        imported_count += 1
    return imported_count
