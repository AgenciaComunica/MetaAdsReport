from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from empresas.forms import EmpresaForm
from empresas.models import Empresa

from .forms import ActiveCompanyForm


def home(request):
    empresas = list(Empresa.objects.order_by('nome'))
    empresa_form = EmpresaForm()
    show_create_modal = False
    show_edit_modal_id = request.GET.get('edit_company', '')
    show_delete_modal_id = request.GET.get('delete_company', '')
    edit_forms = {item.pk: EmpresaForm(instance=item, prefix=f'empresa-{item.pk}') for item in empresas}

    if request.method == 'POST':
        action = request.POST.get('company_action')
        if action == 'update':
            empresa_id = request.POST.get('empresa_id')
            empresa_to_update = get_object_or_404(Empresa, pk=empresa_id)
            edit_form = EmpresaForm(request.POST, instance=empresa_to_update, prefix=f'empresa-{empresa_to_update.pk}')
            if edit_form.is_valid():
                edit_form.save()
                messages.success(request, 'Empresa atualizada com sucesso.')
                return redirect('core:home')
            show_edit_modal_id = str(empresa_to_update.pk)
            edit_forms[empresa_to_update.pk] = edit_form
        else:
            empresa_form = EmpresaForm(request.POST)
            show_create_modal = True
            if empresa_form.is_valid():
                empresa_form.save()
                messages.success(request, 'Empresa cadastrada com sucesso.')
                return redirect('core:home')

    empresa = None
    company_id = request.session.get('active_company_id')
    if company_id:
        empresa = Empresa.objects.filter(pk=company_id).first()
    context = {
        'empresa': empresa,
        'empresas': empresas,
        'active_company_form': ActiveCompanyForm(initial={'empresa': empresa}),
        'empresa_form': empresa_form,
        'show_create_modal': show_create_modal,
        'show_edit_modal_id': str(show_edit_modal_id) if show_edit_modal_id else '',
        'show_delete_modal_id': str(show_delete_modal_id) if show_delete_modal_id else '',
        'edit_forms': edit_forms,
        'edit_company_base_url': reverse('core:home'),
    }
    return render(request, 'core/home.html', context)


def set_active_company(request):
    form = ActiveCompanyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        empresa = form.cleaned_data['empresa']
        if empresa:
            request.session['active_company_id'] = empresa.pk
            messages.success(request, f'Empresa ativa definida como {empresa.nome}.')
        else:
            request.session.pop('active_company_id', None)
            messages.success(request, 'Filtro de empresa removido.')
    return redirect(request.META.get('HTTP_REFERER', 'core:home'))
