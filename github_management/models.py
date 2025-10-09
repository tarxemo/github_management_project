# models.py
from django.db import models
from django.utils import timezone

class Country(models.Model):
    """Model to store available countries from committers.top"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    last_updated = models.DateTimeField(null=True, blank=True)
    user_count = models.PositiveIntegerField(default=0)
    is_fetching = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Countries"
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.name

class GitHubUser(models.Model):
    """Model to store GitHub user information and their statistics."""
    username = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    followers = models.PositiveIntegerField(default=0)
    following = models.PositiveIntegerField(default=0)
    contributions_last_year = models.PositiveIntegerField(default=0)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='users')
    rank = models.PositiveIntegerField(default=0)
    fetched_at = models.DateTimeField(auto_now=True)
    profile_url = models.URLField(max_length=255, blank=True, null=True)
    avatar_url = models.URLField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['-contributions_last_year']
        verbose_name = 'GitHub User'
        verbose_name_plural = 'GitHub Users'
        indexes = [
            models.Index(fields=['country']),
            models.Index(fields=['contributions_last_year']),
            models.Index(fields=['rank']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.country.name}) - {self.contributions_last_year} contributions"
    
    @property
    def full_name(self):
        """Return the full name if available, otherwise return username."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username