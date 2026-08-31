from django.urls import path

from .views import UpgradeCheckView

urlpatterns = [
    path('app/upgrade/', UpgradeCheckView.as_view(), name='app_upgrade_check'),
]
