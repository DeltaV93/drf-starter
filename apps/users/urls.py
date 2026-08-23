from django.urls import path

from .views import MeView
from .views_export import DataExportDownloadView, DataExportRequestView

urlpatterns = [
    path('users/me/', MeView.as_view(), name='user_me'),
    path('account/export/', DataExportRequestView.as_view(), name='data_export_request'),
    path(
        'account/export/<str:token>/',
        DataExportDownloadView.as_view(),
        name='data_export_download',
    ),
]
