from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from utils.api_utils import api_response

from .serializers import UserSerializer, UserUpdateSerializer


class MeView(APIView):
    """Read and update the authenticated user's own profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary='Get the current user', responses={200: UserSerializer})
    def get(self, request):
        return api_response(
            data=UserSerializer(request.user).data,
            message='Profile retrieved.',
        )

    @extend_schema(
        summary='Update the current user',
        request=UserUpdateSerializer,
        responses={200: UserSerializer},
    )
    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user, data=request.data, partial=True, context={'request': request}
        )
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                message='Profile update failed.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        return api_response(data=serializer.data, message='Profile updated.')
