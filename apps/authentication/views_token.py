"""Bearer-token authentication endpoints, for clients with no cookie jar.

The mobile counterpart to `views.py`. Same credentials, same audit trail, same
account-enumeration properties -- what differs is only what the client is
handed at the end: a token pair it stores in the platform keystore rather than
a session cookie the browser stores for it.

    1. POST auth/token/                 -- credentials in, pair out
    2. POST auth/token/2fa/verify/      -- only when the first step said so
    3. POST auth/token/refresh/         -- spend the refresh, get a new pair
    4. POST auth/token/revoke/          -- log out

No CSRF anywhere in that list, and its absence is not an oversight. CSRF
defends against a browser attaching a cookie the user did not ask it to
attach; a client that puts its credential in a header by hand has nothing to
defend. `authentication_classes = []` on these views says so explicitly --
without it, DRF's SessionAuthentication would enforce CSRF on a request that
happened to carry a stale session cookie.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.core.audit import AuditAction, audit
from apps.core.throttles import LoginRateThrottle
from apps.users.serializers import UserSerializer
from utils.api_utils import api_response

from . import token_services, two_factor_services
from .serializers import UserLoginSerializer
from .serializers_token import (
    TokenObtainSerializer,
    TokenPairSerializer,
    TokenRefreshSerializer,
    TokenTwoFactorSerializer,
)


def _invalid(serializer, message):
    return api_response(
        errors=serializer.errors, message=message, status_code=status.HTTP_400_BAD_REQUEST
    )


class TokenObtainView(APIView):
    """Exchange a username and password for a token pair."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginRateThrottle]
    serializer_class = TokenObtainSerializer

    @extend_schema(
        summary='Obtain a token pair',
        request=TokenObtainSerializer,
        # 200 covers both outcomes: signed in, or stopped at the second
        # factor. TokenPairSerializer documents which fields go with which.
        responses={200: TokenPairSerializer},
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            audit(
                AuditAction.LOGIN_FAILED,
                request=request,
                target=str(request.data.get('username', ''))[:254],
                reason='invalid_credentials',
            )
            return _invalid(serializer, 'Login failed.')

        user = serializer.validated_data['user']

        # A correct password is only half of it when a second factor is
        # enrolled. No tokens are minted here -- the challenge is redeemable
        # for nothing except a second-factor attempt.
        if two_factor_services.is_required_for(user):
            return api_response(
                data={
                    'two_factor_required': True,
                    'challenge': token_services.issue_challenge(user),
                },
                message='Enter the code from your authenticator app.',
            )

        audit(AuditAction.LOGIN_SUCCEEDED, actor=user, request=request)
        return api_response(
            data={**token_services.issue_pair(user), 'user': UserSerializer(user).data},
            message='Login successful.',
        )


class TokenTwoFactorVerifyView(APIView):
    """Finish a token login that stopped at the second factor.

    AllowAny because the caller is not authenticated yet -- that is the whole
    point. Authority comes from the signed challenge, which only a successful
    password check can produce.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginRateThrottle]
    serializer_class = TokenTwoFactorSerializer

    @extend_schema(
        summary='Verify a second factor and obtain a token pair',
        request=TokenTwoFactorSerializer,
        responses={200: TokenPairSerializer},
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return _invalid(serializer, 'Verification failed.')

        user = token_services.user_for_challenge(serializer.validated_data['challenge'])
        if user is None:
            return api_response(
                message='That verification has expired. Please sign in again.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            method = two_factor_services.verify(user, serializer.validated_data['code'])
        except two_factor_services.TwoFactorError as exc:
            audit(
                AuditAction.LOGIN_FAILED,
                request=request,
                target=user.get_username(),
                reason='invalid_second_factor',
            )
            return api_response(message=str(exc), status_code=status.HTTP_400_BAD_REQUEST)

        audit(AuditAction.LOGIN_SUCCEEDED, actor=user, request=request)
        return api_response(
            data={
                **token_services.issue_pair(user),
                'user': UserSerializer(user).data,
                'method': method,
            },
            message='Login successful.',
        )


class TokenRefreshView(APIView):
    """Spend a refresh token for a new pair."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [LoginRateThrottle]
    serializer_class = TokenRefreshSerializer

    @extend_schema(
        summary='Refresh a token pair',
        request=TokenRefreshSerializer,
        responses={200: TokenPairSerializer},
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return _invalid(serializer, 'Could not refresh the session.')

        try:
            pair = token_services.refresh_pair(serializer.validated_data['refresh'])
        except token_services.TokenServiceError as exc:
            # 401, not 400: this is the status the client's interceptor
            # watches for to decide it must send the user back to the sign-in
            # screen rather than retry.
            return api_response(message=str(exc), status_code=status.HTTP_401_UNAUTHORIZED)

        return api_response(data=pair, message='Session refreshed.')


class TokenRevokeView(APIView):
    """Log out: blacklist the refresh token so it cannot be spent again."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = TokenRefreshSerializer

    @extend_schema(
        summary='Revoke a refresh token',
        request=TokenRefreshSerializer,
        responses={200: None},
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return _invalid(serializer, 'Could not end the session.')

        try:
            token_services.revoke(serializer.validated_data['refresh'])
        except token_services.TokenServiceError:
            # Deliberately a success. The caller asked for this token to stop
            # working and it does not work; saying so would only make a client
            # retry a logout it has already achieved.
            pass

        return api_response(message='Successfully logged out.')
