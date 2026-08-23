"""Managing your own API keys.

Session-only on purpose: minting a credential with a credential means a leaked
read key can be traded for a write key, and a stolen key can mint replacements
that survive revoking the original.
"""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.core.audit import AuditAction, audit
from utils.api_utils import api_response

from .models import APIKey, generate_key
from .serializers import APIKeyCreateSerializer, APIKeySerializer, CreatedAPIKeySerializer


class APIKeyListCreateView(APIView):
    # Not DEFAULT_AUTHENTICATION_CLASSES: a key must not be able to mint keys.
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='List your API keys', responses={200: APIKeySerializer(many=True)})
    def get(self, request):
        keys = APIKey.objects.filter(user=request.user)
        return api_response(
            data=APIKeySerializer(keys, many=True).data, message='API keys retrieved.'
        )

    @extend_schema(
        summary='Create an API key',
        request=APIKeyCreateSerializer,
        responses={201: CreatedAPIKeySerializer},
    )
    def post(self, request):
        serializer = APIKeyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                message='Could not create the key.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        full_key, prefix, hashed_secret = generate_key()
        key = APIKey.objects.create(
            user=request.user,
            name=serializer.validated_data['name'],
            scope=serializer.validated_data['scope'],
            expires_at=serializer.validated_data.get('expires_at'),
            prefix=prefix,
            hashed_secret=hashed_secret,
        )

        audit(
            AuditAction.API_KEY_CREATED,
            actor=request.user,
            request=request,
            target=key.name,
            prefix=key.prefix,
            scope=key.scope,
        )

        return api_response(
            data={
                **APIKeySerializer(key).data,
                # The only time this value exists outside the caller's hands.
                # It is not recoverable afterwards, by anyone, including staff.
                'key': full_key,
            },
            message='API key created. Copy it now -- it will not be shown again.',
            status_code=status.HTTP_201_CREATED,
        )


class APIKeyDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Revoke an API key', responses={200: APIKeySerializer})
    def delete(self, request, key_id):
        # Revoked rather than deleted: the row is what makes last_used_at and
        # the prefix meaningful when working out what a leaked key reached.
        key = get_object_or_404(APIKey, pk=key_id, user=request.user)
        key.revoke()
        audit(
            AuditAction.API_KEY_REVOKED,
            actor=request.user,
            request=request,
            target=key.name,
            prefix=key.prefix,
        )
        return api_response(data=APIKeySerializer(key).data, message='API key revoked.')
