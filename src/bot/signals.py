from django.db.models.signals import post_save
from django.dispatch import receiver

from bot.models import PDFUpload, Validation
from bot.services import check_and_award_subscription


@receiver(post_save, sender=PDFUpload)
def on_pdfupload_created(sender, instance, created, **kwargs):
    """Сигнал: при создании PDFUpload инкрементим счетчик загрузок
    и проверяем достижение порога подписки.
    """
    if not created or instance.user is None:  # Чтобы не считатать загрузки от бота - условие (or instance.user.is_bot)
        return

    user = instance.user
    user.upload_count = (user.upload_count or 0) + 1
    user.save(update_fields=['upload_count'])

    check_and_award_subscription(user)


@receiver(post_save, sender=Validation)
def on_validation_created(sender, instance, created, **kwargs):
    """Сигнал: при создании Validation инкрементим счетчик проверок
    и проверяем достижение порога подписки.
    """
    if not created or instance.user is None:
        return

    user = instance.user
    user.validation_count = (user.validation_count or 0) + 1
    user.save(update_fields=['validation_count'])

    check_and_award_subscription(user)
