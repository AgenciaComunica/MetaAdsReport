from django.db import models


class ConcorrenteAd(models.Model):
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='anuncios_concorrentes')
    concorrente_nome = models.CharField(max_length=255)
    texto_principal = models.TextField(blank=True)
    titulo = models.CharField(max_length=255, blank=True)
    descricao = models.TextField(blank=True)
    cta = models.CharField(max_length=100, blank=True)
    plataforma = models.CharField(max_length=100, blank=True, default='Meta Ads')
    link = models.URLField(blank=True)
    data_referencia = models.DateField(null=True, blank=True)
    categoria = models.CharField(max_length=100, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_referencia', '-criado_em']
        verbose_name = 'Anúncio de Concorrente'
        verbose_name_plural = 'Anúncios de Concorrentes'

    def __str__(self):
        return f'{self.concorrente_nome} - {self.empresa.nome}'

