from django.conf import settings
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
from .views_token import TokenObtainView, TokenRefreshView, TokenRevokeView

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
    # Bearer tokens, for the mobile client. Registered unconditionally: the
    # browser simply never calls them, and a flag here would mean a template
    # whose mobile app cannot sign in until someone finds the switch.
    path('auth/token/', TokenObtainView.as_view(), name='token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/revoke/', TokenRevokeView.as_view(), name='token_revoke'),
]

if settings.TWO_FACTOR_ENABLED:
    from .views_two_factor import (
        TwoFactorConfirmView,
        TwoFactorDisableView,
        TwoFactorEnrolView,
        TwoFactorRecoveryCodesView,
        TwoFactorStatusView,
        TwoFactorVerifyView,
    )

    urlpatterns += [
        path('auth/2fa/', TwoFactorStatusView.as_view(), name='two_factor_status'),
        path('auth/2fa/enrol/', TwoFactorEnrolView.as_view(), name='two_factor_enrol'),
        path('auth/2fa/confirm/', TwoFactorConfirmView.as_view(), name='two_factor_confirm'),
        path('auth/2fa/disable/', TwoFactorDisableView.as_view(), name='two_factor_disable'),
        path(
            'auth/2fa/recovery-codes/',
            TwoFactorRecoveryCodesView.as_view(),
            name='two_factor_recovery_codes',
        ),
        path('auth/2fa/verify/', TwoFactorVerifyView.as_view(), name='two_factor_verify'),
    ]

    # The token flow's own second step. It cannot share the session one: that
    # view reads the pending login out of the session cookie, and a client
    # holding a signed challenge instead has no session to read.
    from .views_token import TokenTwoFactorVerifyView

    urlpatterns.append(
        path(
            'auth/token/2fa/verify/',
            TokenTwoFactorVerifyView.as_view(),
            name='token_two_factor_verify',
        )
    )

if settings.SOCIAL_AUTH_ENABLED:
    from django.urls import include

    from .views_social import SocialConnectionsView, SocialDisconnectView

    urlpatterns += [
        # social_django's own views handle the redirect out and the callback.
        path('auth/social/', include('social_django.urls', namespace='social')),
        path(
            'auth/social/connections/',
            SocialConnectionsView.as_view(),
            name='social_connections',
        ),
        path(
            'auth/social/connections/<str:provider>/disconnect/',
            SocialDisconnectView.as_view(),
            name='social_disconnect',
        ),
    ]
