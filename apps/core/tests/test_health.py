import pytest
from django.urls import reverse


def test_health_is_public(api_client):
    response = api_client.get(reverse('v1:health'))

    assert response.status_code == 200
    assert response.data['status'] == 'success'
    assert response.data['data']['status'] == 'ok'


@pytest.mark.django_db
def test_readiness_reports_database(api_client):
    response = api_client.get(reverse('v1:readiness'))

    assert response.status_code == 200
    assert response.data['data']['checks']['database'] is True
