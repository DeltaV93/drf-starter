from rest_framework.response import Response
from rest_framework import status


def api_response(data=None, message=None, status_code=status.HTTP_200_OK, errors=None):
    """
    Standardized API response format.

    This is perfect for use in function-based views, or anywhere you need to
    return a standardized response manually.

    :param data: The main response data. Can be a dict, list, or any serializable type. (dict, list, etc.)
    :param message: A string message, usually used for success/error messages
    :param status_code: HTTP status code - Defaults to 200 (OK)
    :param errors: A dictionary of error messages, usually used for form errors
    :return: DRF Response object

    Example:
        # >>> api_response(data={'user': 'John'}, message='User retrieved successfully')
        <Response status_code=200>
        {
            "status": "success",
            "message": "User retrieved successfully",
            "data": {"user": "John"}
        }

        # >>> api_response(errors={'email': 'Invalid email'}, status_code=status.HTTP_400_BAD_REQUEST)
        <Response status_code=400>
        {
            "status": "error",
            "errors": {"email": "Invalid email"}
        }
    """
    response_data = {
        "status": "success" if status.is_success(status_code) else "error",
        "message": message,
        "data": data,
        "errors": errors
    }

    # Remove None values
    response_data = {k: v for k, v in response_data.items() if v is not None}

    return Response(response_data, status=status_code)


class StandardizedResponseMixin:
    """
    A mixin for Django Rest Framework views to standardize API responses.

    This mixin provides methods to create a consistent response structure
    across all API endpoints. It wraps the response data in a standardized
    format including status, message, data, and errors.

    Usage:
        class YourViewClass(StandardizedResponseMixin, APIView):
            ...

    The mixin will automatically format the response for any method that
    returns a DRF Response object.

    Attributes:
        None

    Methods:
        standardized_response: Creates a standardized response dictionary.
        finalize_response: Intercepts and standardizes the response before it's returned.

    Example response format:
        {
            "status": "success" or "error",
            "message": "Operation successful",
            "data": { ... },
            "errors": { ... }
        }
    """

    @staticmethod
    def standardized_response(data=None, message=None, status_code=status.HTTP_200_OK, errors=None):
        """
        Create a standardized response dictionary.

        Args:
            data (dict, optional): The main response data.
            message (str, optional): A message describing the response.
            status_code (int, optional): The HTTP status code. Defaults to 200.
            errors (dict, optional): Any error messages.

        Returns:
            dict: A formatted response dictionary.
        """
        response_data = {
            "status": "success" if status.is_success(status_code) else "error",
            "message": message,
            "data": data,
            "errors": errors
        }
        response_data = {k: v for k, v in response_data.items() if v is not None}
        return Response(response_data, status=status_code)

    def finalize_response(self, request, response, *args, **kwargs):
        """
        Intercept the response and standardize it before returning.

        This method is called by DRF before returning the response. It checks if
        the response is a DRF Response object and if so, it standardizes the
        response format.

        Args:
            request: The request object.
            response: The response object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: A DRF Response object with standardized structure.
        """
        if not isinstance(response, Response):
            return response

        if hasattr(self, 'get_success_headers'):
            success_headers = self.get_success_headers(response.data)
            response.data = self.standardized_response(
                data=response.data,
                status_code=response.status_code
            ).data
            response['Content-Type'] = 'application/json'
            response.status_code = response.status_code
            response['success_headers'] = success_headers
        return super().finalize_response(request, response, *args, **kwargs)
