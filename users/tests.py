from django.test import TestCase, Client
from django.urls import reverse
from users.models import User, UserFollowing
from unittest.mock import patch
from django.conf import settings

class RelationshipAjaxTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com', 
            password='password123',
            github_username='testuser',
            github_access_token='fake_token'
        )
        self.target_user = User.objects.create_user(
            email='target@example.com', 
            password='password123',
            github_username='targetuser'
        )
        # Try to find the backend to use
        backend = settings.AUTHENTICATION_BACKENDS[0]
        self.client.force_login(self.user, backend=backend)

    def test_relationship_management_full_page(self):
        """Test standard GET request returns full page."""
        url = reverse('relationship_management')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/relationship_management.html')

    def test_relationship_management_ajax(self):
        """Test AJAX GET request returns only the partial."""
        url = reverse('relationship_management')
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/partials/user_grid.html')

    @patch('users.services.github_service.GitHubService.follow_user_on_github')
    def test_follow_user_ajax(self, mock_follow):
        """Test follow user via AJAX."""
        url = reverse('follow_user', args=[self.target_user.github_username])
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['is_following'])
        mock_follow.assert_called_once()

    @patch('users.services.github_service.GitHubService.unfollow_user_on_github')
    def test_unfollow_user_ajax(self, mock_unfollow):
        """Test unfollow user via AJAX."""
        UserFollowing.objects.create(from_user=self.user, to_user=self.target_user)
        
        url = reverse('unfollow_user', args=[self.target_user.github_username])
        response = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertFalse(data['is_following'])
        mock_unfollow.assert_called_once()
