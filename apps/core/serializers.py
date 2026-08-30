"""Response shapes for the endpoints that do not use the API envelope.

Declared rather than inferred: `spectacular --fail-on-warn` runs in CI and in
`make check`, and it cannot guess the body of a plain APIView.
"""

from rest_framework import serializers


class AppLinkComponentSerializer(serializers.Serializer):
    path = serializers.CharField(
        source='/',
        help_text='A path pattern the app claims, e.g. /invitations/*.',
    )


class AppLinkDetailSerializer(serializers.Serializer):
    appIDs = serializers.ListField(child=serializers.CharField())
    components = AppLinkComponentSerializer(many=True)


class AppLinksSerializer(serializers.Serializer):
    details = AppLinkDetailSerializer(many=True)


class WebCredentialsSerializer(serializers.Serializer):
    apps = serializers.ListField(child=serializers.CharField())


class AppleAppSiteAssociationSerializer(serializers.Serializer):
    """Apple's association document. The shape is theirs, not ours."""

    applinks = AppLinksSerializer()
    webcredentials = WebCredentialsSerializer()


class AssetLinkTargetSerializer(serializers.Serializer):
    namespace = serializers.CharField()
    package_name = serializers.CharField()
    sha256_cert_fingerprints = serializers.ListField(child=serializers.CharField())


class AssetLinkSerializer(serializers.Serializer):
    """One entry of Google's Digital Asset Links array."""

    relation = serializers.ListField(child=serializers.CharField())
    target = AssetLinkTargetSerializer()
