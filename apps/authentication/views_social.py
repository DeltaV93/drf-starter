"""Listing and unlinking connected providers.

Starting an OAuth flow is social_django's own view, mounted at
/api/v1/auth/social/. These endpoints are what the SPA needs around it.
"""

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from utils.api_utils import api_response


class SocialConnectionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='List connected providers', responses={200: None})
    def get(self, request):
        from social_django.models import UserSocialAuth

        connections = UserSocialAuth.objects.filter(user=request.user)
        return api_response(
            data={
                'providers': [
                    {'provider': c.provider, 'uid': c.uid, 'connected_at': c.created}
                    for c in connections
                ],
                'available': list(settings.SOCIAL_AUTH_PROVIDERS),
                # Whether unlinking everything would leave no way in.
                'has_usable_password': request.user.has_usable_password(),
            },
            message='Connections retrieved.',
        )


class SocialDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Unlink a provider', request=None, responses={200: None})
    def post(self, request, provider):
        from social_django.models import UserSocialAuth

        connections = UserSocialAuth.objects.filter(user=request.user)
        target = connections.filter(provider=provider)

        if not target.exists():
            return api_response(
                message='That provider is not connected.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Refusing to leave someone with no way to sign in. Without a usable
        # password, the last provider is the only credential they have, and
        # password reset cannot help -- there is nothing to reset to.
        others_remain = connections.exclude(provider=provider).exists()
        if not others_remain and not request.user.has_usable_password():
            return api_response(
                message=(
                    'That is the only way you can sign in. Set a password first, '
                    'or connect another provider.'
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        target.delete()
        return api_response(message=f'{provider} disconnected.')
