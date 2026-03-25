from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from types import SimpleNamespace

from .forms import ConfiguracaoUploadEmpresaForm, EmpresaForm, NovaConfiguracaoUploadForm
from .models import ConfiguracaoUploadEmpresa, Empresa
from .upload_config_services import get_field_schema, inspect_uploaded_file


def empresa_list(request):
    return redirect('core:home')


def empresa_create(request):
    form = EmpresaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        empresa = form.save()
        messages.success(request, 'Empresa cadastrada com sucesso.')
        return redirect('empresas:detail', pk=empresa.pk)
    return render(request, 'empresas/form.html', {'form': form, 'title': 'Nova empresa'})


def empresa_update(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    form = EmpresaForm(request.POST or None, instance=empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Empresa atualizada com sucesso.')
        return redirect('empresas:detail', pk=empresa.pk)
    return render(request, 'empresas/form.html', {'form': form, 'title': 'Editar empresa', 'empresa': empresa})


def empresa_detail(request, pk):
    empresa = get_object_or_404(
        Empresa.objects.prefetch_related('configuracoes_upload'),
        pk=pk,
    )
    context = {
        'empresa': empresa,
        'configuracoes_upload': empresa.configuracoes_upload.all(),
        'nova_configuracao_form': NovaConfiguracaoUploadForm(),
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

    preview = None
    uploaded_file = request.FILES.get('arquivo_exemplo')
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

    form = ConfiguracaoUploadEmpresaForm(
        request.POST or None,
        request.FILES or None,
        instance=configuracao,
        columns=preview.columns if preview else configuracao.colunas_detectadas_json,
    )
    if preview_error:
        form.add_error('arquivo_exemplo', preview_error)

    if request.method == 'POST' and form.is_valid():
        configuracao = form.save_configuration(preview=preview)
        messages.success(request, 'Configuração de upload salva com sucesso.')
        return redirect('empresas:upload_config_update', empresa_pk=empresa.pk, config_pk=configuracao.pk)

    mapping_rows = []
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

    context = {
        'empresa': empresa,
        'configuracao': configuracao,
        'form': form,
        'preview_rows': preview.rows if preview else configuracao.preview_json,
        'preview_columns': preview.columns if preview else configuracao.colunas_detectadas_json,
        'mapping_rows': mapping_rows,
    }
    return render(request, 'empresas/upload_config_form.html', context)


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
