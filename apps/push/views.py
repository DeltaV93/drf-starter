"""Registering and unregistering devices for push notifications."""

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from utils.api_utils import api_response

from .models import Device
from .serializers import DeviceRegistrationSerializer, DeviceSerializer


class DeviceListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeviceRegistrationSerializer

    @extend_schema(
        summary='List your registered devices',
        responses={200: DeviceSerializer(many=True)},
    )
    def get(self, request):
        devices = Device.objects.filter(user=request.user)
        return api_response(
            data=DeviceSerializer(devices, many=True).data,
            message='Devices retrieved.',
        )

    @extend_schema(
        summary='Register a device for push notifications',
        request=DeviceRegistrationSerializer,
        responses={200: DeviceSerializer, 201: DeviceSerializer},
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                message='Could not register this device.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        token = serializer.validated_data['token']

        # An upsert keyed on the token alone, not on (user, token). The token
        # identifies an installation, so if it is already known it must move
        # to whoever is registering it now -- otherwise signing in on someone
        # else's phone leaves that phone receiving the previous user's
        # notifications, which is a data leak dressed up as a stale row.
        #
        # `is_active` is reset here too: a token the push service once
        # reported as gone is demonstrably alive again if the app is using it.
        with transaction.atomic():
            device, created = Device.objects.update_or_create(
                token=token,
                defaults={
                    'user': request.user,
                    'platform': serializer.validated_data['platform'],
                    'device_name': serializer.validated_data.get('device_name', ''),
                    'is_active': True,
                },
            )

        return api_response(
            data=DeviceSerializer(device).data,
            message='Device registered.',
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class DeviceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Unregister a device',
        request=None,
        responses={200: None, 404: None},
    )
    def delete(self, request, token):
        # Filtered by user as well as token: without that, knowing any token
        # would be enough to unsubscribe somebody else's phone.
        deleted, _ = Device.objects.filter(user=request.user, token=token).delete()
        if not deleted:
            return api_response(
                message='No such device.', status_code=status.HTTP_404_NOT_FOUND
            )
        return api_response(message='Device unregistered.')
