from django.db import models


class UploadCampanha(models.Model):
    class PeriodoTipo(models.TextChoices):
        SEMANAL = 'semanal', 'Semanal'
        MENSAL = 'mensal', 'Mensal'
        ANUAL = 'anual', 'Anual'
        PERSONALIZADO = 'personalizado', 'Personalizado'

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='uploads_campanha')
    arquivo = models.FileField(upload_to='campanhas/')
    nome_referencia = models.CharField(max_length=255)
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)
    periodo_tipo = models.CharField(max_length=20, choices=PeriodoTipo.choices, default=PeriodoTipo.PERSONALIZADO)
    colunas_mapeadas_json = models.JSONField(default=dict, blank=True)
    observacoes_importacao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Upload de Campanha'
        verbose_name_plural = 'Uploads de Campanha'

    def __str__(self):
        return f'{self.empresa} - {self.nome_referencia}'


class UploadPainel(models.Model):
    configuracao = models.ForeignKey('empresas.ConfiguracaoUploadEmpresa', on_delete=models.CASCADE, related_name='uploads_painel')
    arquivo = models.FileField(upload_to='empresas/painel-uploads/')
    nome_arquivo = models.CharField(max_length=255)
    colunas_detectadas_json = models.JSONField(default=list, blank=True)
    preview_json = models.JSONField(default=list, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Upload de Painel'
        verbose_name_plural = 'Uploads de Painel'

    def __str__(self):
        return f'{self.configuracao.nome} - {self.nome_arquivo}'


class CampanhaMetric(models.Model):
    upload = models.ForeignKey(UploadCampanha, on_delete=models.CASCADE, related_name='metricas')
    fingerprint = models.CharField(max_length=64, db_index=True, blank=True)
    data = models.DateField(null=True, blank=True)
    campanha = models.CharField(max_length=255)
    investimento = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    impressoes = models.BigIntegerField(default=0)
    alcance = models.BigIntegerField(default=0)
    cliques = models.BigIntegerField(default=0)
    ctr = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    cpc = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    cpm = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    resultados = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cpl = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    class Meta:
        ordering = ['campanha', 'data']
        verbose_name = 'Métrica de Campanha'
        verbose_name_plural = 'Métricas de Campanha'

    def __str__(self):
        return f'{self.campanha} ({self.upload.nome_referencia})'
