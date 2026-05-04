from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0008_transactional_email_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspace",
            name="transactional_email_use_ssl",
            field=models.BooleanField(
                default=False,
                help_text="Conexión SMTP cifrada desde el primer byte (típico en puerto 465). No combinar con STARTTLS (Usar TLS) en el mismo servidor.",
                verbose_name="SSL implícito al conectar al SMTP",
            ),
        ),
    ]
