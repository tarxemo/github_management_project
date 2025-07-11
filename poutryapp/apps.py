from django.apps import AppConfig
import poutryapp

class PoutryappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'poutryapp'

    def ready(self):
        import poutryapp.signals