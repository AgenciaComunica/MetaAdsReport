from django.db import models


class AnaliseConcorrencial(models.Model):
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='analises_concorrenciais')
    concorrente_nome = models.CharField(max_length=255, blank=True, db_index=True)
    titulo = models.CharField(max_length=255, default='Análise dos Concorrentes')
    conteudo = models.TextField()
    total_anuncios = models.PositiveIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Análise Concorrencial'
        verbose_name_plural = 'Análises Concorrenciais'

    def __str__(self):
        alvo = self.concorrente_nome or 'Geral'
        return f'{self.empresa.nome} - {alvo} - {self.criado_em:%d/%m/%Y %H:%M}'
