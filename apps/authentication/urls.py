from django.urls import path

from .views import (
    AccountDeletionView,
    CSRFTokenView,
    EmailVerificationView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetValidateView,
    RegisterView,
    ResendVerificationView,
)

urlpatterns = [
    path('auth/csrf/', CSRFTokenView.as_view(), name='csrf_token'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path(
        'auth/password-reset/',
        PasswordResetRequestView.as_view(),
        name='password_reset_request',
    ),
    path(
        'auth/password-reset/<str:uidb64>/<str:token>/',
        PasswordResetValidateView.as_view(),
        name='password_reset_validate',
    ),
    path(
        'auth/password-reset/confirm/',
        PasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
    path('auth/verify-email/', EmailVerificationView.as_view(), name='verify_email'),
    path(
        'auth/verify-email/resend/',
        ResendVerificationView.as_view(),
        name='resend_verification',
    ),
    path('auth/delete-account/', AccountDeletionView.as_view(), name='account_deletion'),
]
