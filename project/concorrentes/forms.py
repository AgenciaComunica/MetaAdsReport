from django import forms

from empresas.models import Empresa

from .models import ConcorrenteAd


class ConcorrenteAdForm(forms.ModelForm):
    class Meta:
        model = ConcorrenteAd
        fields = [
            'empresa',
            'concorrente_nome',
            'texto_principal',
            'titulo',
            'descricao',
            'cta',
            'plataforma',
            'link',
            'data_referencia',
            'categoria',
            'observacoes',
        ]
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'concorrente_nome': forms.TextInput(attrs={'class': 'form-control'}),
            'texto_principal': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cta': forms.TextInput(attrs={'class': 'form-control'}),
            'plataforma': forms.TextInput(attrs={'class': 'form-control'}),
            'link': forms.URLInput(attrs={'class': 'form-control'}),
            'data_referencia': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ConcorrenteImportForm(forms.Form):
    empresa = forms.ModelChoiceField(queryset=Empresa.objects.order_by('nome'), widget=forms.Select(attrs={'class': 'form-select'}))
    arquivo = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))


class InstagramProfileImportForm(forms.Form):
    empresa = forms.ModelChoiceField(queryset=Empresa.objects.order_by('nome'), widget=forms.Select(attrs={'class': 'form-select'}))
    instagram_profile_url = forms.URLField(
        label='URL do perfil do Instagram',
        widget=forms.URLInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'https://www.instagram.com/nome_do_perfil/',
            }
        ),
    )
