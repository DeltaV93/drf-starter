"""The metadata document's shape, declared for the schema.

This is the one endpoint that does not return the `api_response` envelope --
RFC 9728 fixes its shape -- so drf-spectacular has nothing familiar to infer
from and CI runs `spectacular --fail-on-warn`. Declaring it here is also the
cheapest way to keep the document's keys visible to a reader of the API docs.
"""

from rest_framework import serializers


class ProtectedResourceMetadataSerializer(serializers.Serializer):
    resource = serializers.CharField(
        help_text="This resource server's identifier. A token's `aud` must match it exactly."
    )
    authorization_servers = serializers.ListField(
        child=serializers.CharField(),
        help_text='Where to obtain a token. This server issues none.',
    )
    scopes_supported = serializers.ListField(
        child=serializers.CharField(),
        help_text='Scopes worth asking the authorization server for.',
    )
    bearer_methods_supported = serializers.ListField(
        child=serializers.CharField(),
        help_text='How to present a token. Header only.',
    )
