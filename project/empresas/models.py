from django.db import models


class Empresa(models.Model):
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, blank=True)
    segmento = models.CharField(max_length=255, blank=True)
    redes_sociais_json = models.JSONField(default=list, blank=True)
    instagram_profile_url = models.URLField(blank=True)
    ads_biblioteca_ativo = models.BooleanField(default=False)
    ads_biblioteca_query = models.CharField(max_length=255, blank=True)
    ads_biblioteca_sinal = models.PositiveIntegerField(default=0)
    ads_biblioteca_consultado_em = models.DateTimeField(null=True, blank=True)
    seguidores = models.PositiveIntegerField(default=0)
    posts_total_publicos = models.PositiveIntegerField(default=0)
    feed_posts_visiveis = models.PositiveIntegerField(default=0)
    feed_posts_detalhes = models.JSONField(default=list, blank=True)
    feed_datas_publicadas = models.JSONField(default=list, blank=True)
    feed_cadencia = models.CharField(max_length=100, blank=True)
    feed_formatos = models.JSONField(default=dict, blank=True)
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.nome

    @property
    def redes_sociais(self):
        return self.redes_sociais_json or []


class ConfiguracaoUploadEmpresa(models.Model):
    class TipoDocumento(models.TextChoices):
        TRAFEGO_PAGO = 'trafego_pago', 'Tráfego Pago'
        CRM_VENDAS = 'crm_vendas', 'CRM Vendas'
        LEADS_EVENTOS = 'leads_eventos', 'Leads Eventos'

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='configuracoes_upload')
    nome = models.CharField(max_length=255)
    tipo_documento = models.CharField(max_length=40, choices=TipoDocumento.choices, blank=True)
    arquivo_exemplo = models.FileField(upload_to='empresas/upload-configs/', blank=True)
    nome_arquivo_exemplo = models.CharField(max_length=255, blank=True)
    colunas_detectadas_json = models.JSONField(default=list, blank=True)
    preview_json = models.JSONField(default=list, blank=True)
    mapeamento_json = models.JSONField(default=dict, blank=True)
    campos_principais_json = models.JSONField(default=list, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome', 'pk']
        verbose_name = 'Configuração de Upload'
        verbose_name_plural = 'Configurações de Upload'

    def __str__(self):
        return f'{self.empresa.nome} - {self.nome}'
