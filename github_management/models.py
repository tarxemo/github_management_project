# models.py
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from users.services.github_service import GitHubService
from django.urls import reverse
from .managers import GitHubUserManager
from users.abstract_models import BaseUser

class Country(models.Model):
    """Model to store available countries from committers.top"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    last_updated = models.DateTimeField(null=True, blank=True)
    user_count = models.PositiveIntegerField(default=0)
    is_fetching = models.BooleanField(default=False)
    
    def get_absolute_url(self):
        return reverse('github_management:country_detail', kwargs={'slug': self.slug})

    class Meta:
        verbose_name_plural = "Countries"
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.name

class GitHubUser(BaseUser):
    """Model to store GitHub user information and their statistics."""
    country = models.ForeignKey('Country', on_delete=models.CASCADE, related_name='users')
    rank = models.PositiveIntegerField(default=0)
    
    objects = GitHubUserManager()
    
    class Meta:
        verbose_name = 'GitHub User'
        verbose_name_plural = 'GitHub Users'
        indexes = [
            models.Index(fields=['country']),
            models.Index(fields=['rank']),
        ]
    
    def __str__(self):
        return f"{self.github_username} ({self.country.name if self.country else 'No Country'})"
   
    def get_absolute_url(self):
        """Return the canonical URL for this GitHub user."""
        return reverse('github_management:user_detail', kwargs={'github_username': self.github_username})
        
    def is_followed_by(self, user):
        """Check if this GitHub user is already followed by the given user."""
        from users.models import UserFollowing
        if not user or not user.is_authenticated:
            return False
        return UserFollowing.objects.filter(
            from_user=user,
            to_user__github_username__iexact=self.github_username
        ).exists()


class GitHubFollowAction(models.Model):
    """Tracks follow actions to GitHub users and their status."""
    class FollowStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        FOLLOWED_BACK = 'followed_back', 'Followed Back'
        NOT_FOLLOWED_BACK = 'not_followed_back', 'Not Followed Back'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='github_follow_actions'
    )
    github_user = models.ForeignKey(
        GitHubUser,
        on_delete=models.CASCADE,
        related_name='follow_actions'
    )
    status = models.CharField(
        max_length=20,
        choices=FollowStatus.choices,
        default=FollowStatus.PENDING
    )
    followed_at = models.DateTimeField(auto_now_add=True)
    followed_back_at = models.DateTimeField(null=True, blank=True)
    last_checked = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('user', 'github_user')
        ordering = ['-followed_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['followed_at']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user} → {self.github_user} ({self.status})"
    
    def update_follow_status(self):
        """Update the follow status by checking if the user was followed back."""
        from users.models import UserFollowing
        
        self.last_checked = timezone.now()
        
        # Check if the GitHub user is now following back
        is_following_back = UserFollowing.objects.filter(
            from_user__github_username__iexact=self.github_user.github_username,
            to_user=self.user
        ).exists()
        
        if is_following_back:
            self.status = self.FollowStatus.FOLLOWED_BACK
            if not self.followed_back_at:
                self.followed_back_at = timezone.now()
        else:
            self.status = self.FollowStatus.NOT_FOLLOWED_BACK
        
        self.save(update_fields=['status', 'followed_back_at', 'last_checked'])
        return self.status
    
    @classmethod
    def follow_github_user(cls, user, github_user):
        """Create a follow action for a GitHub user."""
        if not user or not user.is_authenticated or not github_user:
            return None
            
        # Check if already following
        existing = cls.objects.filter(
            user=user,
            github_user=GitHubUser.objects.get(id=github_user.id)
        ).first()
        
        if existing:
            return existing
            
        # Create new follow action
        follow_action = cls.objects.create(
            user=user,
            github_user=GitHubUser.objects.get(id=github_user.id),
            status=cls.FollowStatus.PENDING
        )
        GitHubService.follow_user_on_github(user, GitHubUser.objects.get(id=github_user.id).github_username)
        return follow_action
    
    @classmethod
    def unfollow_non_followers(cls, user, days=3):
        """Unfollow users who haven't followed back after specified days."""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get pending follow actions older than specified days
        pending_actions = cls.objects.filter(
            user=user,
            status=cls.FollowStatus.PENDING,
            followed_at__lt=cutoff_date
        )
        
        unfollowed_count = 0
        for action in pending_actions:
            GitHubService.unfollow_user_on_github(user, action.github_user.github_username)
            unfollowed_count += 1
            
        return unfollowed_count