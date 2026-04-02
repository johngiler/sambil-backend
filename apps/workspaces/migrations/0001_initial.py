# Generated manually for workspaces (SaaS owners).

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name="Workspace",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("slug", models.SlugField(help_text="Identificador estable para subdominio y APIs (solo letras minúsculas, números, guiones).", max_length=64, unique=True)),
                ("name", models.CharField(help_text="Nombre comercial del owner (ej. Sambil, Nobis).", max_length=200)),
                ("legal_name", models.CharField(blank=True, help_text="Razón social u organismo propietario (opcional).", max_length=255)),
                ("logo", models.ImageField(blank=True, help_text="Logo principal (marketplace / emails).", null=True, upload_to="workspaces/logos/%Y/%m/")),
                ("logo_mark", models.ImageField(blank=True, help_text="Isotipo o marca reducida (header compacto).", null=True, upload_to="workspaces/logo_marks/%Y/%m/")),
                ("favicon", models.ImageField(blank=True, null=True, upload_to="workspaces/favicons/%Y/%m/")),
                ("primary_color", models.CharField(blank=True, help_text="Color de marca principal (hex, ej. #2c2c81).", max_length=32)),
                ("secondary_color", models.CharField(blank=True, help_text="Color secundario / acentos (hex).", max_length=32)),
                ("support_email", models.EmailField(blank=True, max_length=254)),
                ("marketplace_title", models.CharField(blank=True, help_text="Título corto del marketplace (si vacío, se usa `name`).", max_length=120)),
                ("marketplace_tagline", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "verbose_name": "Workspace (owner)",
                "verbose_name_plural": "Workspaces (owners)",
                "ordering": ["slug"],
            },
        ),
    ]
