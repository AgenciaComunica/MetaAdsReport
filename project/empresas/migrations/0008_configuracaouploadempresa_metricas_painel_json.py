from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0007_empresa_redes_sociais_json'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracaouploadempresa',
            name='metricas_painel_json',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
