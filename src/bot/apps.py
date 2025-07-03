from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError


class BotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bot'
    verbose_name = 'Telegram Chat'

    def ready(self):
        import bot.signals # noqa

        # Создаем запись Config в бд при запуске автоматически,
        # если еще ее нет с дефолтными значениями
        try:
            from bot.models import Config
            if not Config.objects.exists():
                Config.objects.create()
        except (OperationalError, ProgrammingError):
            pass
