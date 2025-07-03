from rest_framework.permissions import BasePermission
from django.conf import settings


class HasValidAPIToken(BasePermission):
    def has_permission(self, request, view):
        return request.headers.get('X-API-Token') == settings.API_SECRET_TOKEN
