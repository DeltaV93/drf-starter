"""Two-factor endpoints.

Enrolling and disabling both require the current password. A session that has
been left open on a shared machine should not be enough to add a factor the
real owner cannot produce, nor to remove the one protecting them.
"""

from django.contrib.auth import login
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.core.audit import AuditAction, audit
from apps.core.throttles import LoginRateThrottle
from apps.users.serializers import UserSerializer
from utils.api_utils import api_response

from . import two_factor_services as services
from .serializers_two_factor import (
    TwoFactorCodeSerializer,
    TwoFactorPasswordSerializer,
    TwoFactorStatusSerializer,
)

PASSWORD_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def _invalid(serializer, message):
    return api_response(
        errors=serializer.errors, message=message, status_code=status.HTTP_400_BAD_REQUEST
    )


def _refused(exc):
    return api_response(message=str(exc), status_code=status.HTTP_400_BAD_REQUEST)


def _reauthenticate(request, serializer):
    """Confirm the current password before a change to the second factor."""
    password = serializer.validated_data['password']
    if not request.user.check_password(password):
        return api_response(
            message='That password is not correct.',
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return None


class TwoFactorStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Two-factor status', responses={200: TwoFactorStatusSerializer})
    def get(self, request):
        device = services.device_for(request.user)
        return api_response(
            data={
                'enabled': bool(device and device.is_confirmed),
                'pending': bool(device and not device.is_confirmed),
                'recovery_codes_remaining': services.unused_recovery_code_count(request.user),
            },
            message='Two-factor status retrieved.',
        )


class TwoFactorEnrolView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Begin two-factor enrolment', request=TwoFactorPasswordSerializer)
    def post(self, request):
        serializer = TwoFactorPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return _invalid(serializer, 'Could not start enrolment.')

        refused = _reauthenticate(request, serializer)
        if refused is not None:
            return refused

        try:
            uri = services.begin_enrolment(request.user)
        except services.TwoFactorError as exc:
            return _refused(exc)

        # The URI carries the secret, which is why it is returned once, here,
        # and by no other endpoint.
        return api_response(
            data={'provisioning_uri': uri},
            message='Scan this in your authenticator, then confirm with a code.',
        )


class TwoFactorConfirmView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(summary='Confirm two-factor enrolment', request=TwoFactorCodeSerializer)
    def post(self, request):
        serializer = TwoFactorCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return _invalid(serializer, 'Could not confirm enrolment.')

        try:
            codes = services.confirm_enrolment(request.user, serializer.validated_data['code'])
        except services.TwoFactorError as exc:
            return _refused(exc)

        return api_response(
            data={'recovery_codes': codes},
            message='Two-factor enabled. Save these recovery codes -- they are shown once.',
        )


class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(summary='Disable two-factor', request=TwoFactorPasswordSerializer)
    def post(self, request):
        serializer = TwoFactorPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return _invalid(serializer, 'Could not disable two-factor.')

        refused = _reauthenticate(request, serializer)
        if refused is not None:
            return refused

        try:
            services.disable(request.user)
        except services.TwoFactorError as exc:
            return _refused(exc)

        return api_response(message='Two-factor disabled.')


class TwoFactorRecoveryCodesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Regenerate recovery codes', request=TwoFactorPasswordSerializer)
    def post(self, request):
        serializer = TwoFactorPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return _invalid(serializer, 'Could not regenerate recovery codes.')

        refused = _reauthenticate(request, serializer)
        if refused is not None:
            return refused

        try:
            codes = services.regenerate_recovery_codes(request.user)
        except services.TwoFactorError as exc:
            return _refused(exc)

        return api_response(
            data={'recovery_codes': codes},
            message='New recovery codes issued. The previous ones no longer work.',
        )


class TwoFactorVerifyView(APIView):
    """Finish a login that stopped at the second factor.

    AllowAny because the caller is not authenticated yet -- that is the whole
    point. Authority comes from the pending state in their own session, which
    only a successful password check can put there.
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(summary='Verify a second factor', request=TwoFactorCodeSerializer)
    def post(self, request):
        user = services.pending_user(request)
        if user is None:
            return api_response(
                message='No login is awaiting verification. Start again.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TwoFactorCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return _invalid(serializer, 'Verification failed.')

        try:
            method = services.verify(user, serializer.validated_data['code'])
        except services.TwoFactorError as exc:
            audit(
                AuditAction.LOGIN_FAILED,
                request=request,
                target=user.get_username(),
                reason='invalid_second_factor',
            )
            return _refused(exc)

        services.clear_pending_login(request)
        # login() cycles the session key, so the half-finished session cannot
        # be replayed as a full one.
        login(request, user, backend=PASSWORD_BACKEND)
        audit(AuditAction.LOGIN_SUCCEEDED, actor=user, request=request)

        from django.middleware.csrf import get_token

        return api_response(
            data={
                'user': UserSerializer(user).data,
                'csrfToken': get_token(request),
                'method': method,
            },
            message='Login successful.',
        )
