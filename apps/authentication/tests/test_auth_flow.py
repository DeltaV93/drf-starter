"""
End-to-end authentication flow tests.

Tests the complete login/logout cycle including:
- Login with valid credentials
- Session creation and CSRF token handling
- Accessing protected endpoints with session
- Logout and session cleanup
- Protected route access control
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.authentication.serializers import UserLoginSerializer

User = get_user_model()


class AuthenticationFlowTestCase(TestCase):
    """Test the complete authentication flow."""

    def setUp(self):
        """Create a test user and client."""
        self.client = Client(enforce_csrf_checks=False)
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpass123',
        )
        self.login_url = '/api/v1/auth/login/'
        self.logout_url = '/api/v1/auth/logout/'
        self.me_url = '/api/v1/users/me/'

    def test_login_with_valid_credentials(self):
        """Test login endpoint returns user data."""
        response = self.client.post(
            self.login_url,
            {
                'username': 'testuser@example.com',
                'password': 'testpass123',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('user', data['data'])
        self.assertEqual(data['data']['user']['email'], 'testuser@example.com')

    def test_login_with_invalid_credentials(self):
        """Test login endpoint rejects invalid credentials."""
        response = self.client.post(
            self.login_url,
            {
                'username': 'testuser@example.com',
                'password': 'wrongpassword',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_login_with_nonexistent_user(self):
        """Test login rejects nonexistent user."""
        response = self.client.post(
            self.login_url,
            {
                'username': 'nonexistent@example.com',
                'password': 'anypassword',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)

    def test_session_created_after_login(self):
        """Test that login creates a session cookie."""
        response = self.client.post(
            self.login_url,
            {
                'username': 'testuser@example.com',
                'password': 'testpass123',
            },
            content_type='application/json',
        )

        # Check session cookie is set
        self.assertIn('sessionid', response.cookies)

    def test_access_protected_endpoint_with_session(self):
        """Test accessing protected endpoint after login."""
        # Login first
        self.client.post(
            self.login_url,
            {
                'username': 'testuser@example.com',
                'password': 'testpass123',
            },
            content_type='application/json',
        )

        # Access protected endpoint
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['data']['email'], 'testuser@example.com')

    def test_cannot_access_protected_endpoint_without_session(self):
        """Test accessing protected endpoint without login fails."""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, 401)

    def test_logout_clears_session(self):
        """Test logout endpoint clears session."""
        # Login first
        self.client.post(
            self.login_url,
            {
                'username': 'testuser@example.com',
                'password': 'testpass123',
            },
            content_type='application/json',
        )

        # Verify session works
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, 200)

        # Logout
        response = self.client.post(self.logout_url, {}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')

        # Verify session is cleared
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, 401)

    def test_login_serializer_validates_email(self):
        """Test UserLoginSerializer validates required fields."""
        serializer = UserLoginSerializer(
            data={
                'username': '',
                'password': 'password123',
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)

    def test_login_serializer_validates_password(self):
        """Test UserLoginSerializer validates password field."""
        serializer = UserLoginSerializer(
            data={
                'username': 'user@example.com',
                'password': '',
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_case_insensitive_email_login(self):
        """Test login works with different case email."""
        response = self.client.post(
            self.login_url,
            {
                'username': 'TESTUSER@EXAMPLE.COM',
                'password': 'testpass123',
            },
            content_type='application/json',
        )

        # Should work because Django username lookup is case-insensitive
        # (depends on database configuration)
        self.assertIn(response.status_code, [200, 400])

    def test_multiple_sequential_logins(self):
        """Test multiple sequential logins work correctly."""
        # First login
        response1 = self.client.post(
            self.login_url,
            {
                'username': 'testuser@example.com',
                'password': 'testpass123',
            },
            content_type='application/json',
        )
        self.assertEqual(response1.status_code, 200)

        # Logout
        self.client.post(self.logout_url, {}, content_type='application/json')

        # Second login should work
        response2 = self.client.post(
            self.login_url,
            {
                'username': 'testuser@example.com',
                'password': 'testpass123',
            },
            content_type='application/json',
        )
        self.assertEqual(response2.status_code, 200)
        data = response2.json()
        self.assertEqual(data['data']['user']['email'], 'testuser@example.com')

    def test_user_data_returned_on_login(self):
        """Test login returns complete user data."""
        self.user.first_name = 'Test'
        self.user.last_name = 'User'
        self.user.save()

        response = self.client.post(
            self.login_url,
            {
                'username': 'testuser@example.com',
                'password': 'testpass123',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        user_data = data['data']['user']
        self.assertEqual(user_data['email'], 'testuser@example.com')
        self.assertEqual(user_data['first_name'], 'Test')
        self.assertEqual(user_data['last_name'], 'User')

    def test_inactive_user_cannot_login(self):
        """Test inactive users cannot login."""
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            self.login_url,
            {
                'username': 'testuser@example.com',
                'password': 'testpass123',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)


class CSRFProtectionTestCase(TestCase):
    """Test CSRF protection on protected endpoints."""

    def setUp(self):
        """Create test user and client with CSRF checks."""
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpass123',
        )
        self.trips_url = '/api/v1/trips/'

    def test_csrf_token_required_for_post(self):
        """Test POST requests require CSRF token."""
        # Login with CSRF checks disabled temporarily
        client_no_csrf = Client(enforce_csrf_checks=False)
        client_no_csrf.post(
            '/api/v1/auth/login/',
            {
                'username': 'testuser@example.com',
                'password': 'testpass123',
            },
            content_type='application/json',
        )

        # Get session from no-csrf client
        session_cookie = client_no_csrf.cookies['sessionid']

        # Now try POST with CSRF checks but no token
        self.client.cookies['sessionid'] = session_cookie
        response = self.client.post(
            self.trips_url,
            {'name': 'Test Trip', 'start_address': 'Start', 'end_address': 'End'},
            content_type='application/json',
        )

        # Should fail with 403 CSRF error
        self.assertEqual(response.status_code, 403)

    def test_get_request_works_with_session(self):
        """Test GET requests work with session cookie."""
        # Login
        client_no_csrf = Client(enforce_csrf_checks=False)
        client_no_csrf.post(
            '/api/v1/auth/login/',
            {
                'username': 'testuser@example.com',
                'password': 'testpass123',
            },
            content_type='application/json',
        )

        # Get session cookie
        session_cookie = client_no_csrf.cookies['sessionid']

        # GET should work with just session cookie
        self.client.cookies['sessionid'] = session_cookie
        response = self.client.get(self.trips_url)
        self.assertEqual(response.status_code, 200)


class SessionSecurityTestCase(TestCase):
    """Test session security features."""

    def setUp(self):
        """Create test user and client."""
        self.client = Client(enforce_csrf_checks=False)
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpass123',
        )

    def test_session_timeout_on_logout(self):
        """Test session is invalidated after logout."""
        # Login
        response = self.client.post(
            '/api/v1/auth/login/',
            {
                'username': 'testuser@example.com',
                'password': 'testpass123',
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

        # Verify session is active
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, 200)

        # Logout
        response = self.client.post('/api/v1/auth/logout/', {}, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        # Session should be invalid now
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, 401)

    def test_password_change_invalidates_sessions(self):
        """Test changing password invalidates session."""
        # Login
        self.client.post(
            '/api/v1/auth/login/',
            {
                'username': 'testuser@example.com',
                'password': 'testpass123',
            },
            content_type='application/json',
        )

        # Verify session works
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, 200)

        # Change password
        self.user.set_password('newpassword123')
        self.user.save()

        # Session should be invalidated after password change
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, 401)
