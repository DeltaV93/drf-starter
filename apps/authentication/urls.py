from django.urls import path

from .views import (
    LoginView, LogoutView, RegisterView, PasswordResetRequestView,
    PasswordResetConfirmView, AccountDeletionView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('password-reset-request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/<str:uidb64>/<str:token>/', PasswordResetConfirmView.as_view(),
         name='password_reset'),
    path('delete-account/', AccountDeletionView.as_view(), name='account_deletion'),
]
