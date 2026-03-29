from django.db import migrations, models


def migrate_instagram_to_social_links(apps, schema_editor):
    Empresa = apps.get_model('empresas', 'Empresa')
    for empresa in Empresa.objects.all():
        if empresa.redes_sociais_json:
            continue
        if empresa.instagram_profile_url:
            empresa.redes_sociais_json = [
                {
                    'network': 'instagram',
                    'label': 'Instagram',
                    'url': empresa.instagram_profile_url,
                }
            ]
            empresa.save(update_fields=['redes_sociais_json'])


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0006_empresa_cnpj'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='redes_sociais_json',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(migrate_instagram_to_social_links, migrations.RunPython.noop),
    ]
