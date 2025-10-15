# users/abstract_models.py
from django.db import models
from django.utils import timezone

class BaseUser(models.Model):
    """Abstract base model for user-related models."""
    github_username = models.CharField(max_length=100, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    followers = models.PositiveIntegerField(default=0)
    following = models.PositiveIntegerField(default=0)
    avatar_url = models.URLField(max_length=255, blank=True, null=True)
    profile_url = models.URLField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    fetched_at = models.DateTimeField(auto_now=True)
    is_updating = models.BooleanField(default=False)
    contributions_last_year = models.PositiveIntegerField(default=0)
    
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
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    def __str__(self):
        return self.github_username or self.email