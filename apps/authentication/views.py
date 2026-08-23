"""Session-cookie authentication endpoints.

The SPA authenticates with Django sessions, so every unsafe request needs a
CSRF token. The flow is:

1. GET  /api/v1/auth/csrf/    -- sets the csrftoken cookie, returns the token
2. POST /api/v1/auth/login/   -- with X-CSRFToken; establishes the session
3.      subsequent requests   -- send the cookie plus X-CSRFToken

``login()`` rotates the CSRF token, so the login response returns the fresh
one for the client to use from then on.
"""

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.middleware.csrf import get_token
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.core.throttles import LoginRateThrottle, PasswordResetRateThrottle
from apps.users.serializers import UserSerializer
from utils.api_utils import api_response
from utils.emails_utils import send_password_reset_email, send_verification_email
from utils.gdpr_utils import anonymize_user_data
from utils.logging_utils import get_logger

from .serializers import (
    AccountDeletionSerializer,
    EmailVerificationSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ResendVerificationSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
)
from .tokens import email_verification_token_generator

User = get_user_model()
logger = get_logger(__name__)

# Answering identically whether or not the address exists is what stops these
# endpoints from being used to enumerate accounts.
GENERIC_EMAIL_RESPONSE = 'If an account exists for that address, we have sent an email.'


def _decode_uid(uidb64):
    """Return the user for a base64-encoded pk, or None if it does not resolve."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        return User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


class CSRFTokenView(APIView):
    """Issue a CSRF cookie. Call this before the first unsafe request."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(summary='Get a CSRF token', responses={200: None})
    def get(self, request):
        return api_response(
            data={'csrfToken': get_token(request)},
            message='CSRF token issued.',
        )


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
    serializer_class = UserRegistrationSerializer

    @extend_schema(summary='Register a new account', request=UserRegistrationSerializer)
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                message='Registration failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()
        _send_verification_email(user)

        # The user is signed in immediately but unverified. Protect whatever
        # must wait for confirmation with the IsEmailVerified permission.
        login(request, user)

        return api_response(
            data={'user': UserSerializer(user).data, 'csrfToken': get_token(request)},
            message='Account created. Check your email to confirm your address.',
            status_code=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
    serializer_class = UserLoginSerializer

    @extend_schema(summary='Log in', request=UserLoginSerializer)
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                message='Login failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.validated_data['user']
        login(request, user)

        return api_response(
            data={
                'user': UserSerializer(user).data,
                # login() rotated the token; hand the new one back.
                'csrfToken': get_token(request),
            },
            message='Login successful.',
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Log out', request=None, responses={200: None})
    def post(self, request):
        logout(request)
        return api_response(message='Successfully logged out.')


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(
        summary='Request a password reset email', request=PasswordResetRequestSerializer
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                message='Invalid data.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data['email']
        user = User.objects.filter(email__iexact=email, is_active=True).first()

        if user is None:
            logger.info('Password reset requested for an address with no active account.')
        else:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f'{settings.FRONTEND_URL}/confirm-password/{uid}/{token}'
            send_password_reset_email(user, reset_url)

        # Same answer either way, and never surfaces whether mail delivery
        # itself succeeded.
        return api_response(message=GENERIC_EMAIL_RESPONSE)


class PasswordResetValidateView(APIView):
    """Check a reset link before showing the new-password form."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(summary='Validate a password reset link', responses={200: None})
    def get(self, request, uidb64, token):
        user = _decode_uid(uidb64)
        is_valid = user is not None and default_token_generator.check_token(user, token)

        return api_response(
            data={'is_valid': is_valid},
            message='Token is valid.' if is_valid else 'Invalid or expired reset link.',
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]
    serializer_class = PasswordResetConfirmSerializer

    @extend_schema(summary='Set a new password', request=PasswordResetConfirmSerializer)
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                message='Invalid data.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = _decode_uid(serializer.validated_data['uid'])
        token = serializer.validated_data['token']

        if user is None or not default_token_generator.check_token(user, token):
            logger.warning('Rejected password reset with an invalid or expired token.')
            return api_response(
                message='Invalid or expired reset link.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        logger.info('Password reset completed for user %s', user.pk)

        return api_response(message='Your password has been reset.')


class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]
    serializer_class = EmailVerificationSerializer

    @extend_schema(summary='Confirm an email address', request=EmailVerificationSerializer)
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                message='Invalid data.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = _decode_uid(serializer.validated_data['uid'])
        token = serializer.validated_data['token']

        if user is None or not email_verification_token_generator.check_token(user, token):
            return api_response(
                message='Invalid or expired verification link.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])
            logger.info('Email verified for user %s', user.pk)

        return api_response(message='Your email address is confirmed.')


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]
    serializer_class = ResendVerificationSerializer

    @extend_schema(
        summary='Resend the verification email', request=ResendVerificationSerializer
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                message='Invalid data.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(
            email__iexact=serializer.validated_data['email'],
            is_active=True,
            email_verified=False,
        ).first()
        if user is not None:
            _send_verification_email(user)

        return api_response(message=GENERIC_EMAIL_RESPONSE)


class AccountDeletionView(APIView):
    """Delete the caller's account.

    Anonymizes rather than hard-deletes, so related records stay intact and
    the deletion is auditable. See utils.gdpr_utils.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AccountDeletionSerializer

    @extend_schema(summary='Delete the current account', request=AccountDeletionSerializer)
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                message='Invalid data provided.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        reason = serializer.validated_data.get('reason') or 'No reason provided'
        logger.info('Account deletion requested for user %s. Reason: %s', user.pk, reason)

        anonymize_user_data(user)
        logout(request)

        return api_response(message='Your account has been deleted.')


def _send_verification_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token_generator.make_token(user)
    verification_url = f'{settings.FRONTEND_URL}/verify-email/{uid}/{token}'
    return send_verification_email(user, verification_url)
