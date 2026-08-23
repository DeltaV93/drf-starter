"""A single response shape for the whole API.

Every endpoint answers with the same envelope so the frontend can handle
success and failure uniformly:

    {"status": "success", "message": "...", "data": {...}}
    {"status": "error",   "message": "...", "errors": {...}}

Keys whose value is None are omitted.
"""

from rest_framework import status
from rest_framework.response import Response


def api_response(data=None, message=None, status_code=status.HTTP_200_OK, errors=None):
    """Build a standardized DRF Response.

    :param data: payload for a successful call
    :param message: human-readable summary
    :param status_code: HTTP status; decides the "status" field
    :param errors: field errors, usually a serializer's ``errors``
    """
    payload = {
        'status': 'success' if status.is_success(status_code) else 'error',
        'message': message,
        'data': data,
        'errors': errors,
    }
    return Response(
        {key: value for key, value in payload.items() if value is not None},
        status=status_code,
    )


class StandardizedResponseMixin:
    """Gives a view ``self.standardized_response(...)``.

    Sugar for views that build several responses; identical in behaviour to
    calling :func:`api_response` directly.
    """

    @staticmethod
    def standardized_response(
        data=None, message=None, status_code=status.HTTP_200_OK, errors=None
    ):
        return api_response(data=data, message=message, status_code=status_code, errors=errors)
