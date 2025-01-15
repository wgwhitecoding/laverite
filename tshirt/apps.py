from django.apps import AppConfig


class TshirtConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tshirt'

    def ready(self):
        import tshirt.signals  # Import the signals module