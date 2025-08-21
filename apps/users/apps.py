from django.apps import AppConfig

class UsersConfig(AppConfig):
    name = 'apps.users'

    def ready(self):
        import apps.users.signals  # 👈 This will activate the signal
