from django import forms
from django.http import QueryDict

from empresas.models import Empresa
from empresas.models import ConfiguracaoUploadEmpresa

from .models import EventoPainel, UploadCampanha, UploadPainel

class UploadCampanhaForm(forms.ModelForm):
    class Meta:
        model = UploadCampanha
        fields = [
            'empresa',
            'arquivo',
            'nome_referencia',
        ]
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'arquivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'nome_referencia': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        empresa_inicial = kwargs.pop('empresa_inicial', None)
        super().__init__(*args, **kwargs)
        self.fields['empresa'].queryset = Empresa.objects.order_by('nome')
        if empresa_inicial:
            self.fields['empresa'].initial = empresa_inicial


class UploadPainelArquivoForm(forms.Form):
    tipo_upload = forms.ChoiceField(
        required=False,
        choices=UploadPainel.TipoUpload.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    arquivo = forms.FileField(
        label='Arquivo',
        widget=forms.FileInput(
            attrs={
                'class': 'form-control',
                'accept': '.csv,.txt,.xlsx,.xls',
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.configuracao = kwargs.pop('configuracao', None)
        super().__init__(*args, **kwargs)
        self.fields['tipo_upload'].choices = [('', 'Selecione o tipo do upload')]
        self.fields['tipo_upload'].widget = forms.Select(attrs={'class': 'form-select'})
        if self.tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS:
            digital_type = str((self.configuracao.configuracao_analise_json or {}).get('digital_type', 'instagram')).strip() if self.configuracao else 'instagram'
            if digital_type == 'instagram':
                self.fields['tipo_upload'].choices += [
                    ('posts', 'Posts'),
                    ('stories', 'Stories'),
                ]
                self.fields['tipo_upload'].required = True
                self.fields['tipo_upload'].label = 'Tipo do upload'
            else:
                self.fields['tipo_upload'].choices += [('principal', 'Arquivo principal')]
                self.fields['tipo_upload'].initial = 'principal'
                self.fields['tipo_upload'].widget = forms.HiddenInput()
        else:
            self.fields['tipo_upload'].widget = forms.HiddenInput()

    @property
    def tipo_documento(self):
        return self.configuracao.tipo_documento if self.configuracao else ''


class ComparePeriodForm(forms.Form):
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
        if args and args[0] is not None:
            bound_data = args[0]
            if isinstance(bound_data, QueryDict):
                bound_data = bound_data.copy()
            else:
                bound_data = bound_data.copy()
            initial = kwargs.get('initial', {}) or {}
            self._merge_default_periods(bound_data, initial)
            args = (bound_data, *args[1:])
        super().__init__(*args, **kwargs)
        self._populate_period_display_fields()

    def _merge_default_periods(self, bound_data, initial):
        defaults = (
            ('data_inicio', initial.get('data_inicio')),
            ('data_fim', initial.get('data_fim')),
            ('data_inicio_anterior', initial.get('data_inicio_anterior')),
            ('data_fim_anterior', initial.get('data_fim_anterior')),
        )
        for key, value in defaults:
            if not bound_data.get(key) and value:
                if hasattr(value, 'strftime'):
                    bound_data[key] = value.strftime('%Y-%m-%d')
                else:
                    bound_data[key] = str(value)
        if not bound_data.get('periodo_atual') and bound_data.get('data_inicio') and bound_data.get('data_fim'):
            bound_data['periodo_atual'] = f"{bound_data['data_inicio']} a {bound_data['data_fim']}"
        if (
            not bound_data.get('periodo_anterior')
            and bound_data.get('data_inicio_anterior')
            and bound_data.get('data_fim_anterior')
        ):
            bound_data['periodo_anterior'] = f"{bound_data['data_inicio_anterior']} a {bound_data['data_fim_anterior']}"

    def _populate_period_display_fields(self):
        def _resolve_value(bound_key, initial_key):
            if self.is_bound:
                value = self.data.get(self.add_prefix(bound_key))
                if value:
                    return value
            return self.initial.get(initial_key)

        def _apply_display(display_field, start_key, end_key):
            current_display = self.data.get(self.add_prefix(display_field)) if self.is_bound else None
            if current_display:
                self.fields[display_field].initial = current_display
                return
            start_value = _resolve_value(start_key, start_key)
            end_value = _resolve_value(end_key, end_key)
            if start_value and end_value:
                if hasattr(start_value, 'strftime') and hasattr(end_value, 'strftime'):
                    self.fields[display_field].initial = f'{start_value:%Y-%m-%d} a {end_value:%Y-%m-%d}'
                else:
                    self.fields[display_field].initial = f'{start_value} a {end_value}'

        _apply_display('periodo_atual', 'data_inicio', 'data_fim')
        _apply_display('periodo_anterior', 'data_inicio_anterior', 'data_fim_anterior')


class EventoPainelForm(forms.ModelForm):
    class Meta:
        model = EventoPainel
        fields = ['nome_evento', 'data_evento', 'impacto', 'leads_media']
        widgets = {
            'nome_evento': forms.TextInput(attrs={'class': 'form-control'}),
            'data_evento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'impacto': forms.Select(attrs={'class': 'form-select'}),
            'leads_media': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1}),
        }


class EventoPainelImportForm(forms.Form):
    arquivo = forms.FileField(
        label='Arquivo',
        widget=forms.FileInput(
            attrs={
                'class': 'form-control',
                'accept': '.xlsx,.xls,.csv',
            }
        ),
    )
