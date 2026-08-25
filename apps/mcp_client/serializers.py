"""What a connection looks like over the API.

Deliberately narrow. The registry says which servers exist, where they live
and which tools they expose; a request can only say *whether this user
authorises one* and supply the token. Nothing here can add a server, change a
URL or widen a tool surface -- those all live in `servers/`, in the
repository.
"""

from rest_framework import serializers


class ConnectableServerSerializer(serializers.Serializer):
    """One available server, with this user's connection state folded in."""

    slug = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    transport = serializers.CharField(read_only=True)
    # Whether the token has to be this user's own, or whether the deployment
    # supplies one. Drives whether the UI asks for a credential.
    requires_user_credential = serializers.BooleanField(read_only=True)
    # The curated surface, or null for "whatever the server offers". Worth
    # showing: it is what the user is agreeing to when they connect.
    allowed_tools = serializers.ListField(
        child=serializers.CharField(), read_only=True, allow_null=True
    )
    connected = serializers.BooleanField(read_only=True)
    enabled = serializers.BooleanField(read_only=True)
    last_used_at = serializers.DateTimeField(read_only=True, allow_null=True)


class ConnectServerSerializer(serializers.Serializer):
    """Authorising a server, or changing an existing authorisation.

    `credential` is write-only and there is no read counterpart anywhere in
    this app's API. A token that can be read back is a token that leaks
    through any endpoint an attacker can reach with a stolen session.
    """

    credential = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
        help_text='The token for this server. Stored encrypted; never returned.',
    )
    enabled = serializers.BooleanField(required=False, default=True)
