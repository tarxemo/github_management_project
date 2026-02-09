# github_management/models_organization.py
from django.db import models
from django.utils import timezone


class GitHubOrganization(models.Model):
    """Model to store GitHub organization data."""
    
    # Organization identification
    github_id = models.BigIntegerField(unique=True, db_index=True)
    node_id = models.CharField(max_length=64, unique=True)
    login = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Organization profile
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    company = models.CharField(max_length=255, null=True, blank=True)
    blog = models.URLField(max_length=500, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    twitter_username = models.CharField(max_length=100, null=True, blank=True)
    
    # URLs
    html_url = models.URLField(max_length=500)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)
    
    # Organization type and verification
    org_type = models.CharField(max_length=50, default='Organization')
    is_verified = models.BooleanField(default=False)
    
    # Metrics
    public_repos = models.PositiveIntegerField(default=0)
    public_gists = models.PositiveIntegerField(default=0)
    followers = models.PositiveIntegerField(default=0)
    following = models.PositiveIntegerField(default=0)
    
    # Billing and plan
    has_organization_projects = models.BooleanField(default=True)
    has_repository_projects = models.BooleanField(default=True)
    
    # Timestamps
    github_created_at = models.DateTimeField()
    github_updated_at = models.DateTimeField()
    fetched_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'GitHub Organization'
        verbose_name_plural = 'GitHub Organizations'
        ordering = ['-public_repos', '-followers']
        indexes = [
            models.Index(fields=['login']),
            models.Index(fields=['-public_repos']),
            models.Index(fields=['-followers']),
        ]
    
    def __str__(self):
        return self.login or self.name or f"Org #{self.github_id}"
