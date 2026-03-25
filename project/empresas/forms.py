from django import forms

from .models import ConfiguracaoUploadEmpresa, Empresa
from .upload_config_services import get_field_schema


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['nome', 'segmento', 'instagram_profile_url', 'observacoes', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'segmento': forms.TextInput(attrs={'class': 'form-control'}),
            'instagram_profile_url': forms.URLInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'https://www.instagram.com/seu_perfil/',
                }
            ),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ConfiguracaoUploadEmpresaForm(forms.ModelForm):
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
        self.mapping_enabled = bool(columns) and bool(self.document_type)
        self.require_mapping = require_mapping and self.mapping_enabled

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

        return cleaned_data

    def save_configuration(self, preview=None):
        instance = self.save(commit=False)
        mapping = {}
        principais = []
        for field_def in get_field_schema(instance.tipo_documento):
            key = field_def['key']
            mapped_column = self.cleaned_data.get(f'map__{key}')
            if mapped_column:
                mapping[key] = mapped_column
            if self.cleaned_data.get(f'primary__{key}'):
                principais.append(key)

        instance.mapeamento_json = mapping
        instance.campos_principais_json = principais
        if preview:
            instance.colunas_detectadas_json = preview.columns
            instance.preview_json = preview.rows
            instance.nome_arquivo_exemplo = preview.file_name
        instance.save()
        return instance

    def save_preview(self, preview):
        instance = self.save(commit=False)
        instance.colunas_detectadas_json = preview.columns
        instance.preview_json = preview.rows
        instance.nome_arquivo_exemplo = preview.file_name
        instance.mapeamento_json = {}
        instance.campos_principais_json = []
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
