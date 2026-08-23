from rest_framework import status

from utils.api_utils import api_response


def test_success_envelope():
    response = api_response(data={'a': 1}, message='Done')

    assert response.status_code == 200
    assert response.data == {'status': 'success', 'message': 'Done', 'data': {'a': 1}}


def test_error_envelope():
    response = api_response(
        errors={'email': ['Required']},
        message='Failed',
        status_code=status.HTTP_400_BAD_REQUEST,
    )

    assert response.data['status'] == 'error'
    assert response.data['errors'] == {'email': ['Required']}


def test_none_values_are_omitted():
    response = api_response(message='Just a message')

    assert set(response.data) == {'status', 'message'}


def test_status_is_derived_from_the_status_code():
    assert api_response(status_code=201).data['status'] == 'success'
    assert api_response(status_code=204).data['status'] == 'success'
    assert api_response(status_code=404).data['status'] == 'error'
    assert api_response(status_code=500).data['status'] == 'error'


def test_falsey_data_is_still_included():
    # An empty list is a meaningful payload; only None is dropped.
    assert api_response(data=[]).data.get('data') == []
