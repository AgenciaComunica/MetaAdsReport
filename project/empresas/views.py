from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from types import SimpleNamespace

from .forms import ConfiguracaoUploadEmpresaForm, EmpresaForm, NovaConfiguracaoUploadForm
from .models import ConfiguracaoUploadEmpresa, Empresa
from .services import strip_empresa_legacy_digital_notes
from .upload_config_services import get_field_schema, get_panel_metric_groups, inspect_uploaded_file


def empresa_list(request):
    return redirect('core:home')


def empresa_create(request):
    return redirect('core:home')


def empresa_update(request, pk):
    get_object_or_404(Empresa, pk=pk)
    return redirect(f"{reverse('core:home')}?edit_company={pk}")


def empresa_detail(request, pk):
    empresa = get_object_or_404(
        Empresa.objects.prefetch_related('configuracoes_upload'),
        pk=pk,
    )
    context = {
        'empresa': empresa,
        'empresa_observacoes': strip_empresa_legacy_digital_notes(empresa.observacoes),
        'configuracoes_upload': empresa.configuracoes_upload.all(),
        'nova_configuracao_form': NovaConfiguracaoUploadForm(),
        'show_delete_upload_id': request.GET.get('delete_upload', ''),
    }
    return render(request, 'empresas/detail.html', context)


def upload_config_create(request, pk):
    empresa = get_object_or_404(
        Empresa.objects.prefetch_related('configuracoes_upload'),
        pk=pk,
    )
    if request.method != 'POST':
        return redirect('empresas:detail', pk=empresa.pk)

    form = NovaConfiguracaoUploadForm(request.POST)
    if form.is_valid():
        configuracao = form.save(commit=False)
        configuracao.empresa = empresa
        configuracao.save()
        messages.success(request, f'Configuração "{configuracao.nome}" criada com sucesso.')
    else:
        for _, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
    return redirect('empresas:detail', pk=empresa.pk)


def upload_config_update(request, empresa_pk, config_pk):
    empresa = get_object_or_404(Empresa, pk=empresa_pk)
    configuracao = get_object_or_404(
        ConfiguracaoUploadEmpresa.objects.select_related('empresa'),
        pk=config_pk,
        empresa=empresa,
    )

    action = request.POST.get('action', 'salvar') if request.method == 'POST' else ''
    uploaded_file = request.FILES.get('arquivo_exemplo')
    preview = None
    preview_error = None
    social_previews = (configuracao.configuracao_analise_json or {}).get('social_previews', {}) if configuracao.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS else {}
    social_example_kind = (
        request.POST.get('social_example_kind')
        or (configuracao.configuracao_analise_json or {}).get('social_example_kind')
        or 'posts'
    )
    if uploaded_file:
        try:
            preview = inspect_uploaded_file(uploaded_file, uploaded_file.name)
        except ValueError as exc:
            preview_error = str(exc)
    elif configuracao.colunas_detectadas_json:
        preview = SimpleNamespace(
            columns=configuracao.colunas_detectadas_json,
            rows=configuracao.preview_json,
            file_name=configuracao.nome_arquivo_exemplo,
        )

    require_mapping = action == 'salvar' and configuracao.tipo_documento != ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS
    form = ConfiguracaoUploadEmpresaForm(
        request.POST or None,
        request.FILES or None,
        instance=configuracao,
        columns=(
            {
                **{kind: data.get('columns', []) for kind, data in social_previews.items()},
                **({social_example_kind: preview.columns} if preview and (request.POST.get('tipo_documento') == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS or configuracao.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS) else {}),
            }
            if (request.POST.get('tipo_documento') == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS or configuracao.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS)
            else (preview.columns if preview else configuracao.colunas_detectadas_json)
        ),
        require_mapping=require_mapping,
    )
    if preview_error:
        form.add_error('arquivo_exemplo', preview_error)

    if request.method == 'POST' and action == 'mapear':
        if not uploaded_file:
            form.add_error('arquivo_exemplo', 'Envie um arquivo para mapear as colunas.')
        elif form.is_valid():
            configuracao = form.save_preview(preview)
            messages.success(request, 'Arquivo lido com sucesso. Agora revise o mapeamento do sistema.')
            return redirect('empresas:upload_config_update', empresa_pk=empresa.pk, config_pk=configuracao.pk)

    if request.method == 'POST' and action == 'limpar_arquivo':
        if configuracao.arquivo_exemplo:
            configuracao.arquivo_exemplo.delete(save=False)
        configuracao.arquivo_exemplo = ''
        configuracao.nome_arquivo_exemplo = ''
        configuracao.save(update_fields=['arquivo_exemplo', 'nome_arquivo_exemplo'])
        messages.success(request, 'Planilha de exemplo removida. Os demais campos foram preservados.')
        return redirect('empresas:upload_config_update', empresa_pk=empresa.pk, config_pk=configuracao.pk)

    if request.method == 'POST' and action == 'salvar':
        has_saved_preview = bool(preview or configuracao.colunas_detectadas_json)
        if form.document_type == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS:
            has_saved_preview = bool(
                preview
                or any((data or {}).get('columns') for data in social_previews.values())
            )
        elif form.document_type == ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS:
            has_saved_preview = True
        if not has_saved_preview:
            form.add_error('arquivo_exemplo', 'Envie um arquivo e clique em Mapear antes de salvar.')
        elif form.is_valid():
            configuracao = form.save_configuration(preview=preview)
            messages.success(request, 'Configuração de upload salva com sucesso.')
            return redirect('empresas:upload_config_update', empresa_pk=empresa.pk, config_pk=configuracao.pk)

    mapping_rows = []
    mapping_sections = []
    if form.mapping_enabled:
        if form.document_type == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS:
            for social_type, social_label in form.social_mapping_types:
                section_rows = []
                for item in get_field_schema(form.document_type, form.digital_type_value):
                    key = item['key']
                    section_rows.append(
                        {
                            'key': key,
                            'label': item['label'],
                            'required': item['required'],
                            'map_field': form[f'map__{social_type}__{key}'],
                            'primary_field': form[f'primary__{social_type}__{key}'],
                        }
                    )
                preview_data = ((configuracao.configuracao_analise_json or {}).get('social_previews', {}) or {}).get(social_type, {})
                mapping_sections.append(
                    {
                        'key': social_type,
                        'label': social_label,
                        'rows': section_rows,
                        'preview_columns': preview_data.get('columns', []),
                        'preview_rows': preview_data.get('rows', []),
                        'file_name': preview_data.get('file_name', ''),
                    }
                )
        else:
            for item in get_field_schema(form.document_type, form.digital_type_value):
                key = item['key']
                mapping_rows.append(
                    {
                        'key': key,
                        'label': item['label'],
                        'required': item['required'],
                        'map_field': form[f'map__{key}'],
                        'primary_field': form[f'primary__{key}'],
                    }
                )

    metric_groups = []
    if form.document_type:
        for group in get_panel_metric_groups(form.document_type, form.digital_type_value):
            metric_groups.append(
                {
                    'key': group['key'],
                    'label': group['label'],
                    'description': group['description'],
                    'metrics': [
                        {
                            'key': item['key'],
                            'label': item['label'],
                            'tooltip': item.get('tooltip', ''),
                            'table_field': form[f'metric_table__{item["key"]}'],
                            'chart_field': form[f'metric_chart__{item["key"]}'],
                        }
                        for item in group['metrics']
                    ],
                    'filter_field': form[f'filter_enabled__{group["key"]}'],
                }
            )

    context = {
        'empresa': empresa,
        'configuracao': configuracao,
        'form': form,
        'preview_rows': preview.rows if preview else configuracao.preview_json,
        'preview_columns': preview.columns if preview else configuracao.colunas_detectadas_json,
        'mapping_rows': mapping_rows,
        'mapping_sections': mapping_sections,
        'metric_groups': metric_groups,
        'show_mapping': (
            any(section['preview_columns'] for section in mapping_sections)
            if form.document_type == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS
            else bool((preview.columns if preview else configuracao.colunas_detectadas_json) and form.document_type)
        ),
        'has_example_file': bool(configuracao.arquivo_exemplo or configuracao.nome_arquivo_exemplo),
    }
    return render(request, 'empresas/upload_config_form.html', context)


def upload_config_delete(request, empresa_pk, config_pk):
    empresa = get_object_or_404(Empresa, pk=empresa_pk)
    configuracao = get_object_or_404(
        ConfiguracaoUploadEmpresa.objects.select_related('empresa'),
        pk=config_pk,
        empresa=empresa,
    )
    if request.method == 'POST':
        nome = configuracao.nome
        if configuracao.arquivo_exemplo:
            configuracao.arquivo_exemplo.delete(save=False)
        configuracao.delete()
        messages.success(request, f'Configuração "{nome}" removida com sucesso.')
        return redirect('empresas:detail', pk=empresa.pk)
    return redirect(f"{reverse('empresas:detail', kwargs={'pk': empresa.pk})}?delete_upload={configuracao.pk}")


def empresa_delete(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        nome = empresa.nome
        if request.session.get('active_company_id') == empresa.pk:
            request.session.pop('active_company_id', None)
        empresa.delete()
        messages.success(request, f'Empresa "{nome}" removida com sucesso. Todos os dados vinculados foram excluídos.')
        return redirect('core:home')
    return render(request, 'empresas/confirm_delete.html', {'empresa': empresa})
