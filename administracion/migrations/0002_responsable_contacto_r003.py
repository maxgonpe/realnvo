# Generated manually for R003

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("administracion", "0001_initial_administracion"),
    ]

    operations = [
        migrations.AddField(
            model_name="responsablerendicion",
            name="area",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="responsablerendicion",
            name="correo",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="responsablerendicion",
            name="telefono",
            field=models.CharField(blank=True, max_length=40),
        ),
    ]
