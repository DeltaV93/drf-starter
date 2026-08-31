from rest_framework import serializers

from .models import AppRelease, Requirement


class UpgradeCheckQuerySerializer(serializers.Serializer):
    """What the client tells us about itself.

    Both fields are required. Guessing the platform from a User-Agent would
    work until it did not, and the version is the whole question.
    """

    platform = serializers.ChoiceField(choices=AppRelease.Platform.choices)
    version = serializers.CharField(max_length=32)


class UpgradeCheckSerializer(serializers.Serializer):
    """What the client is told to do about it."""

    requirement = serializers.ChoiceField(choices=Requirement.CHOICES)
    minimum_version = serializers.CharField(allow_blank=True)
    recommended_version = serializers.CharField(allow_blank=True)
    store_url = serializers.CharField(allow_blank=True)
    message = serializers.CharField(allow_blank=True)
