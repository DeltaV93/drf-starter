from django.urls import path

from .views import (
    AddAddonView,
    CancelSubscriptionView,
    MySubscriptionView,
    PlanListView,
    SubscribeView,
    WebhookView,
)

urlpatterns = [
    path('billing/plans/', PlanListView.as_view(), name='plan_list'),
    path('billing/subscription/', MySubscriptionView.as_view(), name='my_subscription'),
    path(
        'billing/subscribe/<str:stripe_price_id>/',
        SubscribeView.as_view(),
        name='subscribe',
    ),
    path('billing/add-addon/<int:addon_id>/', AddAddonView.as_view(), name='add_addon'),
    path('billing/cancel/', CancelSubscriptionView.as_view(), name='cancel_subscription'),
    path('billing/webhook/', WebhookView.as_view(), name='stripe_webhook'),
]
