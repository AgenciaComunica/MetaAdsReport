from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from types import SimpleNamespace

from .forms import ConfiguracaoUploadEmpresaForm, EmpresaForm, NovaConfiguracaoUploadForm
from .models import ConfiguracaoUploadEmpresa, Empresa
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

    require_mapping = action == 'salvar'
    form = ConfiguracaoUploadEmpresaForm(
        request.POST or None,
        request.FILES or None,
        instance=configuracao,
        columns=preview.columns if preview else configuracao.colunas_detectadas_json,
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
        if not (preview or configuracao.colunas_detectadas_json):
            form.add_error('arquivo_exemplo', 'Envie um arquivo e clique em Mapear antes de salvar.')
        elif form.is_valid():
            configuracao = form.save_configuration(preview=preview)
            messages.success(request, 'Configuração de upload salva com sucesso.')
            return redirect('empresas:upload_config_update', empresa_pk=empresa.pk, config_pk=configuracao.pk)

    mapping_rows = []
    if form.mapping_enabled:
        for item in get_field_schema(form.document_type):
            key = item['key']
            mapping_rows.append(
                {
                    'label': item['label'],
                    'required': item['required'],
                    'map_field': form[f'map__{key}'],
                    'primary_field': form[f'primary__{key}'],
                }
            )

    metric_groups = []
    if form.document_type:
        for group in get_panel_metric_groups(form.document_type):
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
                }
            )

    context = {
        'empresa': empresa,
        'configuracao': configuracao,
        'form': form,
        'preview_rows': preview.rows if preview else configuracao.preview_json,
        'preview_columns': preview.columns if preview else configuracao.colunas_detectadas_json,
        'mapping_rows': mapping_rows,
        'metric_groups': metric_groups,
        'show_mapping': bool((preview.columns if preview else configuracao.colunas_detectadas_json) and form.document_type),
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
