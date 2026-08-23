from django.urls import path

from .views import APIKeyDetailView, APIKeyListCreateView

urlpatterns = [
    path('api-keys/', APIKeyListCreateView.as_view(), name='api_key_list'),
    path('api-keys/<int:key_id>/', APIKeyDetailView.as_view(), name='api_key_detail'),
]
