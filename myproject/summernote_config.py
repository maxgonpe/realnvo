from django_summernote.apps import DjangoSummernoteConfig


class ProjectSummernoteConfig(DjangoSummernoteConfig):
    """
    Mantiene la clave primaria histórica de django-summernote
    compatible con sus migraciones originales.
    """

    default_auto_field = "django.db.models.AutoField"
