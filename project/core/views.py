from django.contrib import messages
from django.shortcuts import redirect, render

from empresas.forms import EmpresaForm
from empresas.models import Empresa


def home(request):
    empresa = Empresa.objects.order_by('pk').first()

    if request.method == 'POST':
        if empresa:
            form = EmpresaForm(request.POST, instance=empresa)
        else:
            form = EmpresaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configurações salvas com sucesso.')
            return redirect('core:home')
    else:
        form = EmpresaForm(instance=empresa) if empresa else EmpresaForm()

    context = {
        'empresa': empresa,
        'form': form,
    }
    return render(request, 'core/home.html', context)
