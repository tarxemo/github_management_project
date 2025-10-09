from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        # Import signals to register them
        import users.signals  # noqa
        # Import tasks to ensure they are registered
        from . import tasks  # noqa
