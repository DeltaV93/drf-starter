import pytest
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from apps.authentication.permissions import IsEmailVerified
from apps.users.factories import UserFactory

pytestmark = pytest.mark.django_db


class _GuardedView(APIView):
    permission_classes = [IsAuthenticated, IsEmailVerified]

    def get(self, request):
        return Response({'ok': True})


def _call_as(user=None):
    request = APIRequestFactory().get('/guarded/')
    if user is not None:
        force_authenticate(request, user=user)
    return _GuardedView.as_view()(request)


def test_a_verified_user_is_allowed():
    assert _call_as(UserFactory(email_verified=True)).status_code == 200


def test_an_unverified_user_is_refused():
    response = _call_as(UserFactory(email_verified=False))

    assert response.status_code == 403


def test_an_anonymous_caller_is_refused():
    assert _call_as().status_code in (401, 403)
