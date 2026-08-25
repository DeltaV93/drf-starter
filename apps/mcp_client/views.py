"""Connecting and disconnecting outbound MCP servers.

Session-only, for the same reason `apps/api_keys` is: authorising a
third-party service with a machine credential means a leaked API key can be
traded for access to everything the user has connected.

What a request can and cannot do is the thing to notice. It can say "I
authorise this server" and hand over a token. It cannot add a server, change
where one lives, or widen its tool surface -- all of that comes from the
modules under `servers/`, which are in the repository and went through review.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from utils.api_utils import api_response

from .models import ConnectedServer
from .registry import UnknownServer, all_servers, get
from .serializers import ConnectableServerSerializer, ConnectServerSerializer


def _describe(definition, connection):
    return {
        'slug': definition.slug,
        'label': definition.label,
        'description': definition.description,
        'transport': definition.transport,
        'requires_user_credential': definition.requires_user_credential,
        'allowed_tools': (
            list(definition.allowed_tools) if definition.allowed_tools is not None else None
        ),
        'connected': connection is not None,
        'enabled': bool(connection and connection.enabled),
        'last_used_at': connection.last_used_at if connection else None,
    }


class ConnectableServerListView(APIView):
    # Not DEFAULT_AUTHENTICATION_CLASSES: authorising a third-party service
    # with a machine credential means a leaked key buys everything the user
    # has connected.
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='List MCP servers you can connect',
        responses={200: ConnectableServerSerializer(many=True)},
    )
    def get(self, request):
        connections = {
            connection.slug: connection
            for connection in ConnectedServer.objects.filter(user=request.user)
        }
        # Driven by the registry, not by the table: a row for a server whose
        # module has been deleted is not a connection anyone can use, and
        # listing it would offer the user something that cannot work.
        data = [
            _describe(definition, connections.get(definition.slug))
            for definition in all_servers()
        ]
        return api_response(
            data=ConnectableServerSerializer(data, many=True).data,
            message='MCP servers retrieved.',
        )


class ConnectedServerDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Connect an MCP server, or change a connection',
        request=ConnectServerSerializer,
        responses={200: ConnectableServerSerializer},
    )
    def put(self, request, slug):
        try:
            definition = get(slug)
        except UnknownServer:
            return api_response(
                message='No such MCP server.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConnectServerSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                message='Could not connect that server.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        connection, _ = ConnectedServer.objects.get_or_create(user=request.user, slug=slug)
        connection.enabled = serializer.validated_data['enabled']

        credential = serializer.validated_data.get('credential')
        if credential:
            connection.set_credential(credential)
        connection.save()

        if definition.requires_user_credential and not connection.credential:
            # Saying so rather than storing a connection that will refuse at
            # the first call, with an error about a missing credential that
            # arrives nowhere near the screen where it was not supplied.
            return api_response(
                errors={'credential': ['This server needs your own token.']},
                message='Could not connect that server.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_response(
            data=ConnectableServerSerializer(_describe(definition, connection)).data,
            message='MCP server connected.',
        )

    @extend_schema(
        summary='Disconnect an MCP server',
        request=None,
        responses={200: ConnectableServerSerializer},
    )
    def delete(self, request, slug):
        try:
            definition = get(slug)
        except UnknownServer:
            return api_response(
                message='No such MCP server.',
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Deleted, not disabled. `enabled` is for pausing a connection while
        # keeping the token; disconnecting is the one that has to actually
        # destroy the credential, or "disconnect" means "still holds your
        # token" and the button lies.
        ConnectedServer.objects.filter(user=request.user, slug=slug).delete()

        return api_response(
            data=ConnectableServerSerializer(_describe(definition, None)).data,
            message='MCP server disconnected.',
        )
