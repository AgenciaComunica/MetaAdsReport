from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EmpresaForm
from .models import Empresa


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
    empresa = get_object_or_404(Empresa, pk=pk)
    return render(request, 'empresas/detail.html', {'empresa': empresa})


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
