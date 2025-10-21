# users/abstract_models.py
from django.db import models
from django.utils import timezone

class BaseUser(models.Model):
    """Abstract base model for user-related models."""
    github_username = models.CharField(max_length=100, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    followers = models.PositiveIntegerField(default=0)
    following = models.PositiveIntegerField(default=0)
    avatar_url = models.URLField(max_length=255, blank=True, null=True)
    profile_url = models.URLField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    fetched_at = models.DateTimeField(auto_now=True)
    is_updating = models.BooleanField(default=False)
    contributions_last_year = models.PositiveIntegerField(default=0)
    # Additional GitHub profile metadata (nullable for backward compatibility)
    github_id = models.BigIntegerField(null=True, blank=True)
    github_node_id = models.CharField(max_length=64, null=True, blank=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    company = models.CharField(max_length=255, null=True, blank=True)
    blog = models.URLField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    email_public = models.EmailField(null=True, blank=True)
    hireable = models.BooleanField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    twitter_username = models.CharField(max_length=100, null=True, blank=True)
    public_repos = models.PositiveIntegerField(default=0)
    public_gists = models.PositiveIntegerField(default=0)
    github_created_at = models.DateTimeField(null=True, blank=True)
    github_updated_at = models.DateTimeField(null=True, blank=True)
    account_type = models.CharField(max_length=50, null=True, blank=True)
    user_view_type = models.CharField(max_length=50, null=True, blank=True)
    site_admin = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['github_username']),
            models.Index(fields=['email']),
            models.Index(fields=['followers']),
            models.Index(fields=['following']),
            models.Index(fields=['contributions_last_year']),
        ]
        ordering = ['-contributions_last_year']
        abstract = True

    @property
    def full_name(self):
        """Return the full name of the user."""
        return f"{self.first_name or ''} {self.middle_name or ''} {self.last_name or ''}".strip()

    def __str__(self):
        return self.github_username or self.email