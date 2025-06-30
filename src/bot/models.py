from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

STATUS = (
    ("pending", "в ожидании"),
    ("completed", "завершено"),
    ("expired", "истекло"),
    ("removed", "удалено"),
)

STATE = (
    ("uploaded", "загружено"),
    ("validated", "проверено"),
    ("deleted", "удалено"),
)

TYPE = (("upload", "загрузка"), ("validation", "валидация"))

REASON = (("uploads", "загрузки"), ("validations", "валидации"))


class ChatUser(AbstractUser):
    """Пользователь."""

    telegram_id = models.BigIntegerField(
        unique=True, null=True, blank=True, verbose_name="Telegram ID"
    )
    username = models.CharField(
        max_length=25, unique=True, null=True, verbose_name="Имя пользователя"
    )
    join_date = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата присоединения"
    )
    is_in_bot = models.BooleanField(
        default=False,
        help_text="Взаимодействовал ли пользователь с ботом",
        verbose_name="Пользователь в боте",
    )
    upload_count = models.BigIntegerField(
        default=0, verbose_name="Количество загрузок"
    )
    validation_count = models.BigIntegerField(
        default=0, verbose_name="Количество валидаций"
    )

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "Пользователи"
        app_label = "bot"

    def __str__(self):
        return f"{self.telegram_id} {self.username}"


class Request(models.Model):
    """Запрос PDF."""

    doi = models.CharField(max_length=256, verbose_name="DOI")
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    expires_at = models.DateTimeField("Дата истечения")
    status = models.CharField(
        max_length=25, choices=STATUS, verbose_name="Статус запроса"
    )
    chat_id = models.BigIntegerField(verbose_name="ID чата")
    user = models.ForeignKey(
        ChatUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requests",
        verbose_name="Пользователь",
    )
    message_id = models.IntegerField(default=0, verbose_name="ID сообщения")
    message_search_id = models.IntegerField(
        default=0, verbose_name="ID сообщения поиска"
    )

    class Meta:
        verbose_name = "запрос"
        verbose_name_plural = "Запросы"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
            self.expires_at = self.created_at + timedelta(
                hours=47
            )  # Так как на удаление сообщения telegram дает до 48 часов
        super().save(*args, **kwargs)

    def __str__(self):
        return f"id={self.pk} DOI={self.doi} created_at={self.created_at}"


class PDFUpload(models.Model):
    """Загрузка PDF."""

    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name="uploads",
        verbose_name="Запрос",
    )
    user = models.ForeignKey(
        ChatUser,
        on_delete=models.CASCADE,
        related_name="uploads",
        verbose_name="Пользователь",
    )
    path = models.CharField(default="", verbose_name="Путь к файлу")
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name="Дата загрузки"
    )
    validated_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата проверки"
    )
    is_valid = models.BooleanField(
        null=True, blank=True, verbose_name="Проверено"
    )
    delete_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата удаления"
    )
    message_id = models.BigIntegerField(default=0, verbose_name="ID сообщения")
    reply_to_message_id = models.BigIntegerField(
        default=0, verbose_name="ID ответа"
    )
    file_id = models.CharField(default="", verbose_name="ID файла")
    state = models.CharField(
        max_length=25, choices=STATE, default="uploaded", verbose_name="Состояние"
    )

    class Meta:
        verbose_name = "загрузка PDF"
        verbose_name_plural = "Загрузки PDF"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
            self.delete_at = self.created_at + timedelta(
                hours=47
            )  # Так как на удаление сообщения telegram дает до 48 часов
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.path} {self.created_at}"


class Validation(models.Model):
    """Валидация PDF."""

    pdf_upload = models.ForeignKey(
        PDFUpload,
        on_delete=models.CASCADE,
        related_name="validations",
        verbose_name="Загрузка PDF",
    )
    user = models.ForeignKey(
        ChatUser,
        on_delete=models.CASCADE,
        related_name="validations",
        verbose_name="Пользователь",
    )
    vote = models.BooleanField(verbose_name="Голос")
    voted_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата голосования"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["pdf_upload", "user"], name="unique_upload"
            ),
        ]
        verbose_name = "валидация"
        verbose_name_plural = "Валидации"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.user == self.pdf_upload.user:
            raise ValidationError(
                "Пользователи не могут валидировать свои собственные загрузки"
            )
        if self.user == self.pdf_upload.request.user:
            raise ValidationError(
                "Создатели запросов не могут валидировать загрузки для своих собственных запросов"
            )

    def __str__(self):
        return f"{self.user} {self.pdf_upload}"


class Notification(models.Model):
    """Уведомление."""

    user = models.ForeignKey(
        ChatUser,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Пользователь",
    )
    type = models.CharField(
        max_length=25, choices=TYPE, verbose_name="Тип уведомления"
    )
    chat_id = models.BigIntegerField(default=0, verbose_name="ID чата")
    chat_message_id = models.BigIntegerField(
        default=0, verbose_name="ID сообщения в чате"
    )
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name="Дата создания"
    )
    delete_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Дата удаления"
    )

    class Meta:
        verbose_name = "уведомление"
        verbose_name_plural = "Уведомления"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
            self.delete_at = self.created_at + timedelta(hours=1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.type} {self.created_at}"


class Subscription(models.Model):
    """Подписка."""

    user = models.ForeignKey(
        ChatUser,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="Пользователь",
    )
    start_date = models.DateTimeField(
        "Дата начала подписки", auto_now_add=True
    )
    end_date = models.DateTimeField("Дата окончания подписки")
    reason = models.CharField(
        max_length=25, choices=REASON, verbose_name="Причина выдачи подписки"
    )

    class Meta:
        verbose_name = "подписка"
        verbose_name_plural = "Подписки"

    def __str__(self):
        return f"{self.user} {self.start_date}"


class Config(models.Model):
    """Model for storing configurable threshold values and other parameters.
    Designed to have only one instance that can be edited through Django Admin.
    """

    uploads_for_subscription = models.PositiveIntegerField(
        default=10,
        help_text="Количество загрузок, необходимых для получения подписки",
        verbose_name="Загрузки для подписки",
    )

    validations_for_subscription = models.PositiveIntegerField(
        default=20,
        help_text="Количество валидаций (голосов), необходимых для получения подписки",
        verbose_name="Валидации для подписки",
    )

    class Meta:
        verbose_name = "Конфигурация"
        verbose_name_plural = "Конфигурации"

    def clean(self):
        """Ensure that only one instance of Config can exist."""
        from django.core.exceptions import ValidationError

        if not self.pk and Config.objects.exists():
            raise ValidationError("Можно создать только одну конфигурацию.")

    def save(self, *args, **kwargs):
        """Override save method to ensure validation is performed before saving."""
        self.full_clean()  # Perform validation
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of Config, creating it if it doesn't exist.
        This ensures there's always a configuration available.
        """
        instance, created = cls.objects.get_or_create(pk=1)
        return instance
