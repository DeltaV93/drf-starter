from django.urls import path
from .views import VaultCreateView, VaultDetailView, DocumentsListView, DocumentDetailView

app_name = 'documents'

urlpatterns = [
    path('vault/create/', VaultCreateView.as_view(), name='vault-create'),
    path('vault/', VaultDetailView.as_view(), name='vault-detail'),
    path('documents/', DocumentsListView.as_view(), name='documents-list'),
    path('documents/<int:pk>/', DocumentDetailView.as_view(), name='documents-detail'),
]
