from django.urls import path

from .views import RequestAPIView

urlpatterns = [
    path('request-pdf/', RequestAPIView.as_view(), name='request-pdf'),
    path('request-pdf/<int:pk>/', RequestAPIView.as_view(), name='request-pdf-detail'),
]
