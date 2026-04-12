from django.db import models


class Relatorio(models.Model):
    class TipoPeriodo(models.TextChoices):
        SEMANAL = 'semanal', 'Semanal'
        MENSAL = 'mensal', 'Mensal'
        ANUAL = 'anual', 'Anual'
        PERSONALIZADO = 'personalizado', 'Personalizado'

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='relatorios')
    titulo = models.CharField(max_length=255)
    periodo_inicio = models.DateField(null=True, blank=True)
    periodo_fim = models.DateField(null=True, blank=True)
    tipo_periodo = models.CharField(max_length=20, choices=TipoPeriodo.choices, default=TipoPeriodo.PERSONALIZADO)
    resumo_ia = models.TextField(blank=True)
    insights_ia = models.TextField(blank=True)
    html_renderizado = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Relatório'
        verbose_name_plural = 'Relatórios'

    def __str__(self):
        return self.titulo

