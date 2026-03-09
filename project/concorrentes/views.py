from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import ConcorrenteAdForm, ConcorrenteImportForm
from .models import ConcorrenteAd
from .services import import_competitor_file


def concorrente_list(request):
    queryset = ConcorrenteAd.objects.select_related('empresa')
    empresa_id = request.GET.get('empresa') or request.session.get('active_company_id')
    if empresa_id:
        queryset = queryset.filter(empresa_id=empresa_id)
    if request.GET.get('concorrente_nome'):
        queryset = queryset.filter(concorrente_nome__icontains=request.GET['concorrente_nome'])
    if request.GET.get('categoria'):
        queryset = queryset.filter(categoria__icontains=request.GET['categoria'])
    if request.GET.get('cta'):
        queryset = queryset.filter(cta__icontains=request.GET['cta'])
    return render(request, 'concorrentes/list.html', {'ads': queryset[:300]})


def concorrente_create(request):
    form = ConcorrenteAdForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Anúncio concorrente cadastrado.')
        return redirect('concorrentes:list')
    return render(request, 'concorrentes/form.html', {'form': form})


def concorrente_import(request):
    form = ConcorrenteImportForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        empresa = form.cleaned_data['empresa']
        uploaded_file = form.cleaned_data['arquivo']
        imported_file_path = uploaded_file.temporary_file_path() if hasattr(uploaded_file, 'temporary_file_path') else None
        if not imported_file_path:
            from django.core.files.storage import default_storage

            temp_path = default_storage.save(f'tmp/{uploaded_file.name}', uploaded_file)
            imported_file_path = default_storage.path(temp_path)
        total = import_competitor_file(empresa, imported_file_path)
        messages.success(request, f'{total} anúncios concorrentes importados.')
        return redirect('concorrentes:list')
    return render(request, 'concorrentes/import_form.html', {'form': form})
