from django.apps import AppConfig


class LogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logs'
    verbose_name = '4. 📊 سیستم لاگ و گزارش‌گیری'

    def ready(self):
        import logs.signals