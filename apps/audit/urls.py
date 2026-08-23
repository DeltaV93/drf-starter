from django.urls import path

from .views import MyAuditLogView

urlpatterns = [
    path('account/activity/', MyAuditLogView.as_view(), name='audit_my_activity'),
]
