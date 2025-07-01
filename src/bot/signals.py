from django.db.models.signals import post_save
from django.dispatch import receiver

from bot.models import Count, Request, PDFUpload, Validation
from bot.services import check_and_award_subscription


@receiver(post_save, sender=PDFUpload)
def on_pdfupload_created(sender, instance, created, **kwargs):
    """
    Сигнал: при создании PDFUpload инкрементим счетчик загрузок
    и проверяем достижение порога подписки.
    """

    # Чтобы не считатать загрузки от бота - условие (or instance.user.is_bot)
    if not created or instance.user is None:
        return

    user = instance.user
    count, _ = Count.objects.get_or_create(user=user)

    count.upload_count = (count.upload_count or 0) + 1
    count.total_upload_count = (count.total_upload_count or 0) + 1
    count.save()

    check_and_award_subscription(user, count)


@receiver(post_save, sender=Validation)
def on_validation_created(sender, instance, created, **kwargs):
    """
    Сигнал: при создании Validation инкрементим счетчик проверок
    и проверяем достижение порога подписки.
    """
    if not created or instance.user is None:
        return

    user = instance.user
    count, _ = Count.objects.get_or_create(user=user)

    count.validation_count = (count.validation_count or 0) + 1
    count.total_validation_count = (count.total_validation_count or 0) + 1
    count.save()

    check_and_award_subscription(user, count)


@receiver(post_save, sender=Request)
def on_request_created(sender, instance, created, **kwargs):
    """Сигнал: при создании Request инкрементим счетчик загрузок."""
    if not created or instance.user is None:
        return

    user = instance.user
    count, _ = Count.objects.get_or_create(user=user)

    count.request_count = (count.request_count or 0) + 1
    count.save()


@receiver(post_save, sender=PDFUpload)
def on_deleted_created(sender, instance, created, **kwargs):
    """Сигнал: при удалении PDF инкрементим счетчик удаленных pdf."""

    if not created or instance.user is None:
        return

    user = instance.user
    count, _ = Count.objects.get_or_create(user=user)

    count.deleted_pdf_count = (count.deleted_pdf_count or 0) + 1
    count.save()
