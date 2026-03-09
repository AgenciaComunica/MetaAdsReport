from django import forms

from empresas.models import Empresa

from .models import UploadCampanha

class UploadCampanhaForm(forms.ModelForm):
    class Meta:
        model = UploadCampanha
        fields = [
            'empresa',
            'arquivo',
            'nome_referencia',
            'data_inicio',
            'data_fim',
            'periodo_tipo',
        ]
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'arquivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'nome_referencia': forms.TextInput(attrs={'class': 'form-control'}),
            'data_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'periodo_tipo': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        empresa_inicial = kwargs.pop('empresa_inicial', None)
        super().__init__(*args, **kwargs)
        self.fields['empresa'].queryset = Empresa.objects.order_by('nome')
        if empresa_inicial:
            self.fields['empresa'].initial = empresa_inicial


class ComparePeriodForm(forms.Form):
    empresa = forms.ModelChoiceField(queryset=Empresa.objects.order_by('nome'), widget=forms.Select(attrs={'class': 'form-select'}))
    periodo_atual = forms.CharField(
        label='Período atual',
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control js-date-range',
                'placeholder': 'Selecione o período atual',
                'data-start-target': 'id_data_inicio',
                'data-end-target': 'id_data_fim',
            }
        ),
    )
    data_inicio = forms.DateField(required=False, widget=forms.HiddenInput())
    data_fim = forms.DateField(required=False, widget=forms.HiddenInput())
    periodo_anterior = forms.CharField(
        label='Período anterior',
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control js-date-range',
                'placeholder': 'Selecione o período anterior',
                'data-start-target': 'id_data_inicio_anterior',
                'data-end-target': 'id_data_fim_anterior',
            }
        ),
    )
    data_inicio_anterior = forms.DateField(required=False, widget=forms.HiddenInput())
    data_fim_anterior = forms.DateField(required=False, widget=forms.HiddenInput())
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            return
        data_inicio = self.initial.get('data_inicio')
        data_fim = self.initial.get('data_fim')
        if data_inicio and data_fim:
            self.fields['periodo_atual'].initial = f'{data_inicio:%Y-%m-%d} a {data_fim:%Y-%m-%d}'
        data_inicio_anterior = self.initial.get('data_inicio_anterior')
        data_fim_anterior = self.initial.get('data_fim_anterior')
        if data_inicio_anterior and data_fim_anterior:
            self.fields['periodo_anterior'].initial = f'{data_inicio_anterior:%Y-%m-%d} a {data_fim_anterior:%Y-%m-%d}'
