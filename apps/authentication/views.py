import logging
import os

from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from utils.api_utils import api_response, StandardizedResponseMixin
from utils.emails_utils import send_password_reset_email
from utils.gdpr_utils import anonymize_user_data
from .serializers.auth_serializers import UserLoginSerializer, UserRegistrationSerializer, \
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer, AccountDeletionSerializer

User = get_user_model()
logger = logging.getLogger(__name__)

FRONTEND_URL = os.environ.get('REACT_APP_YOUR_API_ENDPOINT')


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]

    @csrf_exempt
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        print(serializer.is_valid())
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            csrf_token = get_token(request)
            response = JsonResponse({"message": "Login successful"})
            response.set_cookie(
                'csrftoken',
                csrf_token,
                secure=False,  # Set to True in production
                httponly=False,
                samesite='None',
                domain='localhost',
            )
            print(response.cookies, 'csrftoken')
            return response
        return api_response(
            errors=serializer.errors,
            message="Login failed.",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return api_response(
            message="Successfully logged out.",
            status_code=status.HTTP_200_OK
        )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user)  # This uses session-based login
            return api_response(
                message="User registered successfully.",
                status_code=status.HTTP_201_CREATED
            )
        return api_response(
            errors=serializer.errors,
            message="Registration failed.",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class PasswordResetRequestView(StandardizedResponseMixin, APIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                reset_url = f"{FRONTEND_URL}/reset-password/{uid}/{token}/"
                is_email_sent = send_password_reset_email(user, reset_url)
                if is_email_sent:
                    return self.standardized_response(
                        message="If the email exists, a password reset link has been sent.",
                        status_code=status.HTTP_200_OK
                    )
            except User.DoesNotExist:
                logger.warning(f"Password reset attempted for non-existent email: {email}")
                return self.standardized_response(
                    message="If the email exists, a password reset link has been sent.",
                    status_code=status.HTTP_200_OK
                )
        return self.standardized_response(
            errors=serializer.errors,
            message="Invalid data",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class PasswordResetConfirmView(StandardizedResponseMixin, APIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def get(self, request, uidb64, token):

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            logger.warning(f"Invalid password reset token check attempt: {uidb64}")
            return self.standardized_response(
                data={"is_valid": False},
                message="Invalid reset link",
                status_code=status.HTTP_200_OK
            )

        if default_token_generator.check_token(user, token):
            logger.info(f"Valid token for password reset: {user.email}")
            return self.standardized_response(
                data={"is_valid": True},
                message="Token is valid",
                status_code=status.HTTP_200_OK
            )
        else:
            logger.warning(f"Invalid token for password reset: {token}")
            return self.standardized_response(
                data={"is_valid": False},
                message="Invalid or expired token",
                status_code=status.HTTP_200_OK)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            password = serializer.validated_data['password']

            try:
                uid = serializer.validated_data['uid']
                uid = force_str(urlsafe_base64_decode(uid))
                user = User.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                logger.warning(f"Invalid password reset attempt: {token}")
                return self.standardized_response(
                    message="Invalid reset link",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            if default_token_generator.check_token(user, token):
                user.set_password(password)
                user.save()
                logger.info(f"Password reset successful for user: {user.email}")
                return self.standardized_response(
                    message="Password has been reset successfully.",
                    status_code=status.HTTP_200_OK
                )
            else:
                logger.warning(f"Invalid token for password reset: {token}")
                return self.standardized_response(
                    message="Invalid reset link",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        return self.standardized_response(
            errors=serializer.errors,
            message="Invalid data",
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AccountDeletionView(APIView):
    """
    View for handling account deletion requests.

    This view follows GDPR best practices by anonymizing user data instead of hard deletion.
    It also captures the reason for account deletion for analytics purposes.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AccountDeletionSerializer

    def post(self, request):
        """
        Handle POST requests for account deletion.

        :param request: The HTTP request object
        :return: API response indicating success or failure of the account deletion process
        """
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            reason = serializer.validated_data.get('reason', 'No reason provided')

            # Log the account deletion request
            logger.info(f"Account deletion requested for user {user.id}. Reason: {reason}")

            try:
                # Anonymize user data
                anonymize_user_data(user)

                # Log out the user
                logout(request)

                # Log successful account deletion
                logger.info(f"Account successfully anonymized for user {user.id}")

                return api_response(
                    message="Your account has been successfully deleted.",
                    status_code=status.HTTP_200_OK
                )
            except Exception as e:
                # Log the error
                logger.error(f"Error during account deletion for user {user.id}: {str(e)}")
                return api_response(
                    message="An error occurred while processing your request.",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            return api_response(
                errors=serializer.errors,
                message="Invalid data provided.",
                status_code=status.HTTP_400_BAD_REQUEST
            )


def get_csrf_token(request):
    csrf_token = get_token(request)
    return JsonResponse({'csrfToken': csrf_token})


class ProfileView(APIView):
    @permission_classes([IsAuthenticated])
    def get(self, request):
        logger.info(f"User authenticated: {request.user.is_authenticated}")
        logger.info(f"User: {request.user}")
        logger.info(f"Session: {request.session.session_key}")

        return JsonResponse({"message": "You're logged in!"})