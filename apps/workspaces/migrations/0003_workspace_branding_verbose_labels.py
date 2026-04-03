import apps.workspaces.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0002_workspace_branding_svg_filefield"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workspace",
            name="logo",
            field=models.FileField(
                blank=True,
                help_text="Marca completa con tipografía (logotipo). Cabecera amplia, pie, emails. Formatos: SVG, PNG, JPEG, GIF o WebP.",
                null=True,
                upload_to="workspaces/logos/%Y/%m/",
                validators=[apps.workspaces.validators.validate_brand_graphic],
                verbose_name="Logo (logotipo completo)",
            ),
        ),
        migrations.AlterField(
            model_name="workspace",
            name="logo_mark",
            field=models.FileField(
                blank=True,
                help_text="Símbolo o marca reducida sin el nombre extendido (header compacto, favicon si no subes uno aparte). Mismos formatos que el logo.",
                null=True,
                upload_to="workspaces/logo_marks/%Y/%m/",
                validators=[apps.workspaces.validators.validate_brand_graphic],
                verbose_name="Isotipo",
            ),
        ),
        migrations.AlterField(
            model_name="workspace",
            name="favicon",
            field=models.FileField(
                blank=True,
                help_text="Icono de pestaña del navegador. SVG, PNG, ICO, JPEG, GIF o WebP.",
                null=True,
                upload_to="workspaces/favicons/%Y/%m/",
                validators=[apps.workspaces.validators.validate_favicon_file],
                verbose_name="Favicon",
            ),
        ),
        migrations.AlterField(
            model_name="workspace",
            name="primary_color",
            field=models.CharField(
                blank=True,
                help_text="Hex (ej. #2c2c81). Tema y acentos del marketplace.",
                max_length=32,
                verbose_name="Color primario",
            ),
        ),
        migrations.AlterField(
            model_name="workspace",
            name="secondary_color",
            field=models.CharField(
                blank=True,
                help_text="Hex. Acentos secundarios (ej. badges, CTAs alternos).",
                max_length=32,
                verbose_name="Color secundario",
            ),
        ),
        migrations.AlterField(
            model_name="workspace",
            name="support_email",
            field=models.EmailField(
                blank=True,
                help_text="Contacto público del operador (p. ej. pie de página o avisos).",
                max_length=254,
                verbose_name="Correo de soporte",
            ),
        ),
        migrations.AlterField(
            model_name="workspace",
            name="marketplace_title",
            field=models.CharField(
                blank=True,
                help_text="Nombre corto que ve el visitante (si está vacío, se usa el nombre del workspace).",
                max_length=120,
                verbose_name="Título del marketplace",
            ),
        ),
        migrations.AlterField(
            model_name="workspace",
            name="marketplace_tagline",
            field=models.CharField(
                blank=True,
                help_text="Frase corta opcional (propuesta de valor). Sale en la API pública; la interfaz del marketplace aún puede no mostrarla hasta conectarla en el front.",
                max_length=255,
                verbose_name="Eslogan / subtítulo",
            ),
        ),
    ]
