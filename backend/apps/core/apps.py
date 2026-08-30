from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"

    def ready(self):
        # Register Celery tasks after Django has fully initialized so
        # autodiscovery can resolve every INSTALLED_APPS `tasks` module.
        from config.celery import app as celery_app

        celery_app.autodiscover_tasks()