from django.urls import path

from .views import DeviceDetailView, DeviceListCreateView

urlpatterns = [
    path('push/devices/', DeviceListCreateView.as_view(), name='push_device_list'),
    # `str` rather than `slug`: a push token is not a slug. An Expo token is
    # `ExponentPushToken[...]`, and an APNs one is bare hex -- neither fits a
    # slug pattern, and a mismatch here would 404 every unregister.
    path('push/devices/<str:token>/', DeviceDetailView.as_view(), name='push_device_detail'),
]
