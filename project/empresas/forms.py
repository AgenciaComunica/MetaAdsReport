from django import forms
import json

from .models import ConfiguracaoUploadEmpresa, Empresa
from .upload_config_services import get_field_schema, get_panel_metric_groups, get_panel_metric_schema, normalize_panel_metric_config


SEGMENTO_CHOICES = [
    ('', 'Selecione um segmento'),
    ('Industria', 'Indústria'),
    ('Comercio', 'Comércio'),
    ('Servicos', 'Serviços'),
    ('Tecnologia', 'Tecnologia'),
    ('Saude', 'Saúde'),
    ('Educacao', 'Educação'),
    ('Financeiro', 'Financeiro'),
    ('Imobiliario', 'Imobiliário'),
    ('Alimentos e Bebidas', 'Alimentos e Bebidas'),
    ('Moda e Beleza', 'Moda e Beleza'),
    ('Logistica', 'Logística'),
    ('Turismo e Hotelaria', 'Turismo e Hotelaria'),
    ('Agro', 'Agro'),
    ('Outro', 'Outro'),
]

SOCIAL_NETWORK_CHOICES = [
    ('instagram', 'Instagram'),
    ('facebook', 'Facebook'),
    ('linkedin', 'LinkedIn'),
    ('youtube', 'YouTube'),
    ('tiktok', 'TikTok'),
    ('x', 'X / Twitter'),
    ('site', 'Site'),
    ('whatsapp', 'WhatsApp'),
    ('outro', 'Outro'),
]

SOCIAL_NETWORK_LABELS = dict(SOCIAL_NETWORK_CHOICES)


class EmpresaForm(forms.ModelForm):
    segmento = forms.ChoiceField(
        choices=SEGMENTO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    redes_sociais_payload = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Empresa
        fields = ['nome', 'cnpj', 'segmento', 'observacoes', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        redes = self.instance.redes_sociais_json if self.instance.pk else []
        if not redes and self.instance.instagram_profile_url:
            redes = [
                {
                    'network': 'instagram',
                    'label': SOCIAL_NETWORK_LABELS['instagram'],
                    'url': self.instance.instagram_profile_url,
                }
            ]
        self.fields['redes_sociais_payload'].initial = json.dumps(redes, ensure_ascii=False)

    def clean_redes_sociais_payload(self):
        payload = self.cleaned_data.get('redes_sociais_payload', '').strip()
        if not payload:
            return []

        try:
            items = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError('Não foi possível interpretar a lista de redes sociais.') from exc

        if not isinstance(items, list):
            raise forms.ValidationError('Formato inválido para redes sociais.')

        redes = []
        for item in items:
            if not isinstance(item, dict):
                continue
            network = (item.get('network') or '').strip()
            url = (item.get('url') or '').strip()
            if not network and not url:
                continue
            if not network:
                raise forms.ValidationError('Selecione a rede social antes de salvar.')
            if network not in SOCIAL_NETWORK_LABELS:
                raise forms.ValidationError('Rede social inválida.')
            if not url:
                raise forms.ValidationError('Informe a URL da rede social.')
            try:
                forms.URLField().clean(url)
            except forms.ValidationError as exc:
                raise forms.ValidationError(f'URL inválida para {SOCIAL_NETWORK_LABELS[network]}.') from exc
            redes.append(
                {
                    'network': network,
                    'label': SOCIAL_NETWORK_LABELS[network],
                    'url': url,
                }
            )
        return redes

    def save(self, commit=True):
        instance = super().save(commit=False)
        redes = self.cleaned_data.get('redes_sociais_payload', [])
        instance.redes_sociais_json = redes
        instagram_url = ''
        for item in redes:
            if item.get('network') == 'instagram':
                instagram_url = item.get('url', '')
                break
        instance.instagram_profile_url = instagram_url
        if commit:
            instance.save()
        return instance


class ConfiguracaoUploadEmpresaForm(forms.ModelForm):
    crm_origem_paga_contem = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Ex.: utm_source=meta, gclid, fbclid. Se a URL começar com https://www. ou contiver esse parâmetro, será tráfego pago.',
            }
        ),
    )

    class Meta:
        model = ConfiguracaoUploadEmpresa
        fields = ['nome', 'tipo_documento', 'arquivo_exemplo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'arquivo_exemplo': forms.FileInput(
                attrs={
                    'class': 'form-control',
                    'accept': '.csv,.txt,.xlsx,.xls',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        columns = kwargs.pop('columns', None) or []
        require_mapping = kwargs.pop('require_mapping', True)
        super().__init__(*args, **kwargs)
        self.fields['tipo_documento'].required = True
        choices = [('', 'Selecione uma coluna')] + [(column, column) for column in columns]
        principais = set(self.instance.campos_principais_json or [])
        self.document_type = (
            self.data.get(self.add_prefix('tipo_documento'))
            if self.is_bound and self.data.get(self.add_prefix('tipo_documento'))
            else self.instance.tipo_documento
        )
        self.fields['crm_origem_paga_contem'].initial = (self.instance.configuracao_analise_json or {}).get('crm_origem_paga_contem', '')
        self.mapping_enabled = bool(columns) and bool(self.document_type)
        self.require_mapping = require_mapping and self.mapping_enabled
        metric_config = normalize_panel_metric_config(self.document_type, self.instance.metricas_painel_json)

        if self.document_type:
            for group in get_panel_metric_groups(self.document_type):
                filter_state = (metric_config.get('filters') or {}).get(group['key'], {'enabled': False})
                self.fields[f'filter_enabled__{group["key"]}'] = forms.BooleanField(
                    required=False,
                    label=f'Habilitar filtro em {group["label"]}',
                    initial=filter_state.get('enabled', False),
                    widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
                )
                for metric_def in group['metrics']:
                    key = metric_def['key']
                    metric_state = metric_config['metrics'].get(key, {'table': True, 'chart': True})
                    self.fields[f'metric_table__{key}'] = forms.BooleanField(
                        required=False,
                        label=f'{metric_def["label"]} - Tabela',
                        initial=metric_state.get('table', True),
                        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
                    )
                    self.fields[f'metric_chart__{key}'] = forms.BooleanField(
                        required=False,
                        label=f'{metric_def["label"]} - Gráfico',
                        initial=metric_state.get('chart', True),
                        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
                    )

        if not self.mapping_enabled:
            return

        for field_def in get_field_schema(self.document_type):
            key = field_def['key']
            self.fields[f'map__{key}'] = forms.ChoiceField(
                choices=choices,
                required=self.require_mapping and field_def['required'],
                label=field_def['label'],
                initial=(self.instance.mapeamento_json or {}).get(key, ''),
                widget=forms.Select(attrs={'class': 'form-select'}),
            )
            self.fields[f'primary__{key}'] = forms.BooleanField(
                required=False,
                label='Principal',
                initial=(key in principais) or field_def['required'],
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            )

    def clean(self):
        cleaned_data = super().clean()
        selected_columns = {}
        if not self.mapping_enabled:
            if self.document_type:
                cleaned_data['metricas_painel_json'] = self._build_metric_config(cleaned_data)
            return cleaned_data

        for field_def in get_field_schema(cleaned_data.get('tipo_documento') or self.document_type):
            key = field_def['key']
            mapped_column = cleaned_data.get(f'map__{key}')
            if not mapped_column:
                continue
            previous_key = selected_columns.get(mapped_column)
            if previous_key:
                self.add_error(f'map__{key}', f'A coluna "{mapped_column}" já foi usada em outro campo do sistema.')
            selected_columns[mapped_column] = key

        if self.document_type:
            cleaned_data['metricas_painel_json'] = self._build_metric_config(cleaned_data)
            for group in get_panel_metric_groups(self.document_type):
                group_has_any_metric = any(
                    cleaned_data.get(f'metric_table__{metric["key"]}') or cleaned_data.get(f'metric_chart__{metric["key"]}')
                    for metric in group['metrics']
                )
                if not group_has_any_metric:
                    continue
                has_table = any(
                    cleaned_data.get(f'metric_table__{metric["key"]}')
                    for metric in group['metrics']
                )
                has_chart = any(
                    cleaned_data.get(f'metric_chart__{metric["key"]}')
                    for metric in group['metrics']
                )
                if not has_table:
                    raise forms.ValidationError(f'Ative ao menos uma métrica de Tabela em "{group["label"]}".')
                if not has_chart:
                    raise forms.ValidationError(f'Ative ao menos uma métrica de Gráfico em "{group["label"]}".')

        return cleaned_data

    def _build_metric_config(self, cleaned_data):
        if not self.document_type:
            return {'categories': {}, 'metrics': {}, 'filters': {}}

        metricas = {'categories': {}, 'metrics': {}, 'filters': {}}
        for group in get_panel_metric_groups(self.document_type):
            group_key = group['key']
            group_is_active = False
            for metric_def in group['metrics']:
                key = metric_def['key']
                table_enabled = bool(cleaned_data.get(f'metric_table__{key}'))
                chart_enabled = bool(cleaned_data.get(f'metric_chart__{key}'))
                metricas['metrics'][key] = {
                    'table': table_enabled,
                    'chart': chart_enabled,
                }
                if table_enabled or chart_enabled:
                    group_is_active = True
            metricas['categories'][group_key] = group_is_active
            metricas['filters'][group_key] = {
                'enabled': bool(cleaned_data.get(f'filter_enabled__{group_key}')),
            }
        return metricas

    def save_configuration(self, preview=None):
        instance = self.save(commit=False)
        instance.nome = self.cleaned_data.get('nome', instance.nome)
        instance.tipo_documento = self.cleaned_data.get('tipo_documento', instance.tipo_documento)
        mapping = {}
        principais = []
        metricas = self.cleaned_data.get('metricas_painel_json') or {'categories': {}, 'metrics': {}}
        for field_def in get_field_schema(instance.tipo_documento):
            key = field_def['key']
            mapped_column = self.cleaned_data.get(f'map__{key}')
            if mapped_column:
                mapping[key] = mapped_column
            if self.cleaned_data.get(f'primary__{key}'):
                principais.append(key)

        instance.mapeamento_json = mapping
        instance.campos_principais_json = principais
        instance.metricas_painel_json = metricas
        instance.configuracao_analise_json = {
            **(instance.configuracao_analise_json or {}),
            'crm_origem_paga_contem': self.cleaned_data.get('crm_origem_paga_contem', '').strip(),
        }
        if preview:
            instance.colunas_detectadas_json = preview.columns
            instance.preview_json = preview.rows
            instance.nome_arquivo_exemplo = preview.file_name
        instance.save()
        return instance

    def save_preview(self, preview):
        instance = self.save(commit=False)
        instance.nome = self.cleaned_data.get('nome', instance.nome)
        instance.tipo_documento = self.cleaned_data.get('tipo_documento', instance.tipo_documento)
        instance.colunas_detectadas_json = preview.columns
        instance.preview_json = preview.rows
        instance.nome_arquivo_exemplo = preview.file_name
        instance.mapeamento_json = {}
        instance.campos_principais_json = []
        instance.configuracao_analise_json = {
            **(instance.configuracao_analise_json or {}),
            'crm_origem_paga_contem': self.cleaned_data.get('crm_origem_paga_contem', '').strip(),
        }
        instance.save()
        return instance


class NovaConfiguracaoUploadForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoUploadEmpresa
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ex.: Meta Ads Março, CRM Comercial, Financeiro Matriz',
                }
            ),
        }
