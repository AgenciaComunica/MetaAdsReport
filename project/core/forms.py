from django import forms

from empresas.models import Empresa


class ActiveCompanyForm(forms.Form):
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.filter(ativo=True).order_by('nome'),
        required=False,
        empty_label='Todas as empresas',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )

