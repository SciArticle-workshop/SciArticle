from django.urls import path

from .views import RequestAPIView, ValidateBrokenPDFView

urlpatterns = [
    path('request-pdf/', RequestAPIView.as_view(), name='request-pdf'),
    path('request-pdf/<int:pk>/',
         RequestAPIView.as_view(),
         name='request-pdf-detail'),
    path('validate_broken-pdf/',
         ValidateBrokenPDFView.as_view(),
         name='validate_broken-pdf')
]
