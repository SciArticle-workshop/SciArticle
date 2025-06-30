from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from bot.models import (
    ChatUser,
    Config,
    Notification,
    PDFUpload,
    Request,
    Subscription,
    Validation
)


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    """Админка для модели Config."""

    list_display = [
        'id',
        'uploads_for_subscription',
        'validations_for_subscription'
    ]
    readonly_fields = ['id']

    def has_add_permission(self, request):
        return not Config.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    """Админка для модели Request."""

    list_display = ['doi', 'created_at', 'expires_at', 'status', 'chat_id']
    list_filter = ['status', 'created_at']
    search_fields = ['doi', 'chat_id']
    readonly_fields = ['created_at', 'expires_at']
    list_per_page = 20


@admin.register(PDFUpload)
class PDFUploadAdmin(admin.ModelAdmin):
    """Админка для модели PDFUpload."""

    list_display = [
        'request',
        'path',
        'created_at',
        'validated_at',
        'is_valid',
        'delete_at'
    ]
    list_filter = ['is_valid', 'created_at']
    search_fields = ['request__doi']
    readonly_fields = ['created_at', 'delete_at']


@admin.register(Validation)
class ValidationAdmin(admin.ModelAdmin):
    """Админка для модели Validation."""

    list_display = ['pdf_upload', 'user_id', 'vote', 'voted_at']
    list_filter = ['vote', 'voted_at']
    search_fields = ['pdf_upload__request__doi', 'user_id']
    readonly_fields = ['voted_at']


@admin.register(ChatUser)
class ChatUserAdmin(admin.ModelAdmin):
    """Админка для модели ChatUser."""

    list_display = [
        'telegram_id',
        'username',
        'date_joined'
    ]
    list_filter = ['date_joined']
    search_fields = ['telegram_id', 'username']
    readonly_fields = ['date_joined']
    fieldsets = [
        ("Основная информация", {"fields": ["username", "telegram_id", "password"]}),
        ("Статистика", {"fields": ["upload_count", "validation_count"]}),
        (
            "Права доступа",
            {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]},
        ),
        ("Даты", {"fields": ["date_joined", "last_login"]}),
    ]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Админка для модели Notification."""

    list_display = [
        'user',
        'type',
        'chat_message_id',
        'created_at',
        'delete_at'
    ]
    list_filter = ['type', 'created_at']
    search_fields = ['user__username', 'user__telegram_id']
    readonly_fields = ['created_at', 'delete_at']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Админка для модели Subscription."""

    list_display = ['user', 'start_date', 'end_date', 'is_active']
    list_filter = ['start_date', 'end_date']
    search_fields = ['user__username', 'user__telegram_id']
    readonly_fields = ['start_date']

    def is_active(self, obj):
        """Проверяет, активна ли подписка в данный момент."""
        active = obj.end_date > timezone.now()
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if active else 'red',
            'Активна' if active else 'Истекла'
        )
    is_active.short_description = 'Статус'


admin.site.site_header = 'Управление научными статьями'
admin.site.site_title = 'Административная панель'
admin.site.index_title = 'Панель управления'
