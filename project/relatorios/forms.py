from django import forms

from empresas.models import Empresa
from core.utils import last_complete_month_ranges
from relatorios.models import Relatorio


class RelatorioGeracaoForm(forms.Form):
    empresa = forms.ModelChoiceField(queryset=Empresa.objects.order_by('nome'), widget=forms.Select(attrs={'class': 'form-select'}))
    titulo = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    tipo_periodo = forms.ChoiceField(choices=Relatorio.TipoPeriodo.choices, widget=forms.Select(attrs={'class': 'form-select'}))
    periodo_inicio = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    periodo_fim = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            return
        default_ranges = last_complete_month_ranges()
        self.fields['periodo_inicio'].initial = default_ranges['current_start']
        self.fields['periodo_fim'].initial = default_ranges['current_end']
        self.fields['tipo_periodo'].initial = Relatorio.TipoPeriodo.MENSAL
        self.fields['titulo'].initial = f"Relatorio {default_ranges['current_start']:%m/%Y}"
