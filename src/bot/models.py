from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

STATUS = (
    ('pending', 'в ожидании'),
    ('completed', 'завершенный'),
    ('expired', 'истекший'),
    ('removed', 'удаленный'),
)

STATE = (
    ('uploaded', 'загружено'),
    ('validated', 'проверено'),
    ('deleted', 'удалено'),
)

TYPE = (('upload', 'загрузка'), ('validation', 'проверка'))

REASON = (('uploads', 'загрузки'), ('validations', 'проверки'))


class ChatUser(AbstractUser):
    """Пользователь."""

    telegram_id = models.BigIntegerField(
        unique=True, null=True, blank=True, verbose_name='Telegram ID'
    )
    username = models.CharField(
        max_length=25, unique=True, null=True, verbose_name='Имя пользователя'
    )
    join_date = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата присоединения'
    )
    is_bot = models.BooleanField(default=False, verbose_name='Это бот')

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.telegram_id} {self.username}"


class Request(models.Model):
    """Запрос PDF."""

    doi = models.CharField(max_length=256, verbose_name='DOI')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    expires_at = models.DateTimeField('Дата истечения срока')
    status = models.CharField(
        max_length=25,
        choices=STATUS,
        verbose_name='Статус запроса'
    )
    chat_id = models.BigIntegerField(verbose_name='ID чата')
    user = models.ForeignKey(
        ChatUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requests',
        verbose_name='Пользователь'
    )
    message_id = models.IntegerField(default=0, verbose_name='ID сообщения')
    message_search_id = models.IntegerField(
        default=0, verbose_name='ID сообщения в чате'
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
        related_name='uploads',
        verbose_name='Запрос'
    )
    user = models.ForeignKey(
        ChatUser,
        on_delete=models.CASCADE,
        related_name='uploads',
        verbose_name='Пользователь'
    )
    path = models.CharField(default='', verbose_name='Путь к файлу')
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name='Дата создания'
    )
    validated_at = models.DateTimeField(
        null=True, blank=True, verbose_name='Дата проверки'
    )
    is_valid = models.BooleanField(
        null=True, blank=True, verbose_name='Валидный/Невалидный'
    )
    delete_at = models.DateTimeField(
        null=True, blank=True, verbose_name='Дата удаления из чата'
    )
    message_id = models.BigIntegerField(default=0, verbose_name='ID сообщения')
    reply_to_message_id = models.BigIntegerField(
        default=0, verbose_name='ID reply сообщения'
    )
    file_id = models.CharField(default='', verbose_name='Уникальный ID файла')
    state = models.CharField(
        max_length=25, choices=STATE, default='', verbose_name='Сосотояние'
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
        related_name='validations',
        verbose_name='Загруженный pdf файл'
    )
    user = models.ForeignKey(
        ChatUser,
        on_delete=models.CASCADE,
        related_name='validations',
        verbose_name='Пользователь'
    )
    vote = models.BooleanField(verbose_name='Голос')
    voted_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата голосования'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['pdf_upload', 'user'], name='unique_upload'
            ),
        ]
        verbose_name = "валидация"
        verbose_name_plural = "Валидации"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.user == self.pdf_upload.user:
            raise ValidationError(
                'Пользователи, загрузившие статью, не могут участвовать в проверке'
            )
        if self.user == self.pdf_upload.request.user:
            raise ValidationError(
                'Пользователи, запросившие статью, не могут участвовать в проверке'
            )

    def __str__(self):
        return f"{self.user} {self.pdf_upload}"


class Notification(models.Model):
    """Уведомление."""

    user = models.ForeignKey(
        ChatUser,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Пользователь'
    )
    type = models.CharField(
        max_length=25,
        choices=TYPE,
        verbose_name='Тип: загрузка pdf/проверка pdf'
    )
    chat_id = models.BigIntegerField(default=0, verbose_name='ID чата')
    chat_message_id = models.BigIntegerField(
        default=0, verbose_name='ID сообщения в чате'
    )
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name='Дата создания'
    )
    delete_at = models.DateTimeField(
        null=True, blank=True, verbose_name='Дата удаления'
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
        related_name='subscriptions',
        verbose_name='Пользователь'
    )
    start_date = models.DateTimeField('Дата начала подписки')
    end_date = models.DateTimeField('Дата окончания подписки')

    class Meta:
        verbose_name = "подписка"
        verbose_name_plural = "Подписки"

    def __str__(self):
        return f'{self.user} {self.start_date} {self.end_date}'


class Config(models.Model):
    """
    Модель для хранения настраиваемых пороговых значений:
    счетчика загрузок и счетчика проверок.
    Счетчики можно редактировать через админку Django.
    """

    uploads_for_subscription = models.PositiveIntegerField(
        default=10,
        help_text='Количество загрузок pdf, необходимое для подписки')

    validations_for_subscription = models.PositiveIntegerField(
        default=20,
        help_text='Количество проверок pdf, необходимое для подписки')

    class Meta:
        verbose_name = 'Конфигурация'
        verbose_name_plural = 'Конфигурации'

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
        """
        Get the singleton instance of Config,
        creating it if it doesn't exist.
        This ensures there's always a configuration available.
        """
        instance, created = cls.objects.get_or_create(pk=1)
        return instance

    def __str__(self):
        return f'{self.uploads_for_subscription} {self.validations_for_subscription}'


class Count(models.Model):
    """
    Счетчики:
    - количество запросов на PDF
    - количество загрузок PDF
    - количество проверок;
    - количество проверок, количество удаленных PDF
    - количество подписок, полученных за поверку
    - количество подписок, полученных за загрузку.
    """

    user = models.OneToOneField(
        ChatUser,
        on_delete=models.CASCADE,
        related_name='counts',
        verbose_name='Пользователь'
    )
    request_count = models.PositiveBigIntegerField(
        default=0, verbose_name='Запрос'
    )
    upload_count = models.PositiveBigIntegerField(
        default=0, verbose_name='Счетчик загрузок pdf'
    )
    total_upload_count = models.PositiveBigIntegerField(
        default=0,
        verbose_name='Счетчик всех pdf файлов, которые загрузил пользователь'
    )  # Все загрузки пользователя
    validation_count = models.PositiveBigIntegerField(
        default=0, verbose_name='Счетчик проверок пользователя'
    )
    total_validation_count = models.PositiveBigIntegerField(
        default=0,
        verbose_name='Счетчик всех pdf файлов, которые проверил пользователь'
    )  # Все проверки пользователя
    deleted_pdf_count = models.PositiveBigIntegerField(
        default=0, verbose_name='Счетчик всех pdf, которые были удалены')
    subscriptions_for_upload = models.PositiveBigIntegerField(
        default=0, verbose_name='Счетчик подписок за загрузку pdf файлов'
    )
    subscriptions_for_validation = models.PositiveBigIntegerField(
        default=0, verbose_name='Счетчик подписок, полученных за голосование'
    )

    class Meta:
        verbose_name = 'счетчик'
        verbose_name_plural = 'Счетчики'

    def __str__(self):
        return f'{self.user.telegram_id} {self.user.username}'
