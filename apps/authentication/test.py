import factory
import time
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.db import transaction
from django.core import mail
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')


class AuthTestCase(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

        # URLs
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.register_url = reverse('register')
        self.password_reset_request_url = reverse('password_reset_request')
        self.password_reset_confirm_url = reverse('password_reset_confirm')
        self.account_deletion_url = reverse('account-deletion')

    @transaction.atomic
    def test_login(self):
        self.client.force_authenticate(user=None)
        data = {'username': self.user.username, 'password': 'testpass123'}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Successfully logged in', response.data['message'])

    @transaction.atomic
    def test_login_failure(self):
        self.client.force_authenticate(user=None)
        data = {'username': self.user.username, 'password': 'wrongpassword'}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Login failed', response.data['message'])

    @transaction.atomic
    def test_login_invalid_data(self):
        self.client.force_authenticate(user=None)
        data = {'username': 'user', 'password': 123}  # Invalid password type
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def test_logout(self):
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Successfully logged out', response.data['message'])

    @transaction.atomic
    def test_register(self):
        self.client.force_authenticate(user=None)
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword123',
            'password2': 'newpassword123'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('User registered successfully', response.data['message'])

    @transaction.atomic
    def test_register_failure(self):
        self.client.force_authenticate(user=None)
        data = {
            'username': self.user.username,
            'email': self.user.email,
            'password': 'newpassword123',
            'password2': 'newpassword123'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Registration failed', response.data['message'])

    @transaction.atomic
    def test_register_invalid_data(self):
        self.client.force_authenticate(user=None)
        data = {
            'username': 'new user',  # Invalid username with space
            'email': 'invalid-email',
            'password': 'short',
            'password2': 'not_matching'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    @patch('apps.authentication.views.send_password_reset_email')
    def test_password_reset_request(self, mock_send_email):
        self.client.force_authenticate(user=None)
        data = {'email': self.user.email}
        response = self.client.post(self.password_reset_request_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email.assert_called_once()

    @transaction.atomic
    def test_password_reset_confirm(self):
        self.client.force_authenticate(user=None)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        data = {
            'token': f"{uid}-{token}",
            'password': 'newpassword123'
        }
        response = self.client.post(self.password_reset_confirm_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Password has been reset successfully', response.data['message'])

    @transaction.atomic
    def test_password_reset_confirm_invalid_token(self):
        self.client.force_authenticate(user=None)
        data = {
            'token': 'invalid-token',
            'password': 'newpassword123'
        }
        response = self.client.post(self.password_reset_confirm_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def test_account_deletion(self):
        data = {
            'password': 'testpass123',
            'reason': 'Testing account deletion'
        }
        response = self.client.post(self.account_deletion_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that the user is anonymized
        updated_user = User.objects.get(id=self.user.id)
        self.assertFalse(updated_user.is_active)
        self.assertNotEqual(updated_user.username, self.user.username)
        self.assertNotEqual(updated_user.email, self.user.email)
        self.assertEqual(updated_user.first_name, 'Deleted')
        self.assertEqual(updated_user.last_name, 'User')

    @transaction.atomic
    def test_account_deletion_wrong_password(self):
        data = {
            'password': 'wrongpassword',
            'reason': 'Testing account deletion'
        }
        response = self.client.post(self.account_deletion_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def test_account_deletion_unauthenticated(self):
        self.client.force_authenticate(user=None)
        data = {
            'password': 'testpass123',
            'reason': 'Testing account deletion'
        }
        response = self.client.post(self.account_deletion_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PerformanceTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.users = UserFactory.create_batch(100)
        self.login_url = reverse('login')

    def test_login_performance(self):
        start_time = time.time()
        for user in self.users[:10]:  # Test with first 10 users
            data = {'username': user.username, 'password': 'testpass123'}
            response = self.client.post(self.login_url, data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        end_time = time.time()

        total_time = end_time - start_time
        average_time = total_time / 10

        print(f"Average login time: {average_time:.4f} seconds")
        self.assertLess(average_time, 0.5)  # Assumes login should take less than 0.5 seconds on average
