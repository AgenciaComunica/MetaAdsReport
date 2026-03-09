from django.contrib import messages
from django.shortcuts import redirect, render

from empresas.models import Empresa

from .forms import ActiveCompanyForm


def home(request):
    empresa = None
    company_id = request.session.get('active_company_id')
    if company_id:
        empresa = Empresa.objects.filter(pk=company_id).first()
    context = {
        'empresa': empresa,
        'empresas': Empresa.objects.order_by('nome'),
        'active_company_form': ActiveCompanyForm(initial={'empresa': empresa}),
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
