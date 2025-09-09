from django.apps import AppConfig


class ExtintoresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'extintores'

    def ready(self):
        import extintores.signals
