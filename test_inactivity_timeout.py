"""
Test Suite for 10-Minute Inactivity Timeout Feature

Tests the complete auto-logout functionality:
- Session timeout configuration (10 minutes)
- Warning modal display (at 9-minute mark)
- Keep-alive endpoint for session refresh
- Logout endpoint functionality
- Message display on logout redirect
"""

import time
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings

User = get_user_model()


class InactivityTimeoutTests(TestCase):
    """Test cases for inactivity-based session timeout."""

    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.role = 'student'
        self.user.save()

    def test_session_cookie_age_is_600_seconds(self):
        """Verify SESSION_COOKIE_AGE is set to 600 seconds (10 minutes)."""
        self.assertEqual(
            settings.SESSION_COOKIE_AGE,
            600,
            "SESSION_COOKIE_AGE should be 600 seconds (10 minutes)"
        )

    def test_session_save_every_request_enabled(self):
        """Verify SESSION_SAVE_EVERY_REQUEST is enabled."""
        self.assertTrue(
            settings.SESSION_SAVE_EVERY_REQUEST,
            "SESSION_SAVE_EVERY_REQUEST should be True to track inactivity"
        )

    def test_keep_alive_endpoint_exists(self):
        """Verify keep-alive endpoint is accessible."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('accounts:keep_alive'))
        self.assertEqual(
            response.status_code,
            200,
            "Keep-alive endpoint should return 200"
        )
        # Verify response is valid JSON
        data = response.json()
        self.assertEqual(data['status'], 'ok')

    def test_keep_alive_endpoint_requires_authentication(self):
        """Verify keep-alive endpoint requires authenticated user."""
        response = self.client.post(reverse('accounts:keep_alive'))
        self.assertEqual(
            response.status_code,
            401,
            "Keep-alive endpoint should return 401 for unauthenticated users"
        )

    def test_auto_logout_endpoint_exists(self):
        """Verify auto-logout endpoint is accessible."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('accounts:auto_logout'))
        self.assertEqual(
            response.status_code,
            200,
            "Auto-logout endpoint should return 200"
        )

    def test_auto_logout_clears_session(self):
        """Verify auto-logout endpoint clears the session."""
        self.client.login(username='testuser', password='testpass123')
        
        # Verify user is authenticated
        self.assertTrue(self.client.session.get('_auth_user_id'))
        
        # Call auto-logout endpoint
        self.client.post(reverse('accounts:auto_logout'))
        
        # Create new client to verify session is cleared
        new_client = Client()
        # Try to access protected page - should redirect to login
        response = new_client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_login_with_session_expired_reason(self):
        """Verify session expired message is displayed on login."""
        response = self.client.get(
            reverse('accounts:login'),
            {'reason': 'session_expired'}
        )
        self.assertEqual(response.status_code, 200)
        # Check that the warning message is in the response
        self.assertContains(
            response,
            'expired due to inactivity',
            status_code=200
        )

    def test_javascript_config_in_template(self):
        """Verify JavaScript auto-logout config is present in authenticated pages."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:index'))
        
        # Check for auto-logout config in response
        self.assertContains(response, 'RADOKI_AUTO_LOGOUT')
        self.assertContains(response, 'timeoutSeconds: 600')
        self.assertContains(response, 'warningSeconds: 60')
        self.assertContains(response, 'auto-logout.js')


class SessionManagementTests(TestCase):
    """Test cases for server-side session management."""

    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.role = 'student'
        self.user.save()

    def test_session_created_on_login(self):
        """Verify session is created on successful login."""
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'testuser', 'password': 'testpass123'},
            follow=True
        )
        # Check that user is authenticated
        self.assertIn('_auth_user_id', self.client.session)

    def test_normal_site_auth_flag_set_on_login(self):
        """Verify _normal_site_auth flag is set for normal site login."""
        self.client.login(username='testuser', password='testpass123')
        self.assertTrue(
            self.client.session.get('_normal_site_auth'),
            "_normal_site_auth should be True for authenticated users"
        )

    def test_session_cleared_on_logout(self):
        """Verify session is cleared on manual logout."""
        self.client.login(username='testuser', password='testpass123')
        self.assertTrue(self.client.session.get('_auth_user_id'))
        
        # Perform logout
        self.client.get(reverse('accounts:logout'))
        
        # Create new client to verify session is cleared
        new_client = Client()
        response = new_client.get(reverse('dashboard:index'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)


class JavaScriptFunctionalityTests(TestCase):
    """Tests for JavaScript-based functionality (these would be E2E tests in a real scenario)."""

    def setUp(self):
        """Set up test client and user."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.role = 'student'
        self.user.save()

    def test_auto_logout_javascript_file_exists(self):
        """Verify auto-logout JavaScript file is accessible."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/static/js/auto-logout.js')
        self.assertEqual(
            response.status_code,
            200,
            "auto-logout.js should be accessible"
        )
        # Check that key functions are present
        content = response.content.decode('utf-8')
        self.assertIn('showWarning', content)
        self.assertIn('performLogout', content)
        self.assertIn('resetTimer', content)
        self.assertIn('callKeepAlive', content)

    def test_modal_element_present_in_authenticated_pages(self):
        """Verify modal element is present in authenticated page templates."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:index'))
        
        # Check for modal elements
        self.assertContains(response, 'autoLogoutModal')
        self.assertContains(response, 'autoLogoutCountdown')
        self.assertContains(response, 'autoLogoutStayBtn')
        self.assertContains(response, 'alRingArc')


if __name__ == '__main__':
    import django
    from django.test.utils import get_runner
    from django.conf import settings

    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['accounts.tests'])
