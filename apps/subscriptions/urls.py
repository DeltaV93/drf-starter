from django.urls import path
from .views import SubscribeView, AddAddonView, WebhookView

# app_name = 'subscriptions'

urlpatterns = [
    path('subscribe/<str:stripe_price_id>/', SubscribeView.as_view(), name='subscribe'),
    path('add-addon/<int:addon_id>/', AddAddonView.as_view(), name='add_addon'),
    path('webhook/', WebhookView.as_view(), name='webhook'),
]