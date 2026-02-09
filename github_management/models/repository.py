# github_management/models/github_repository.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class GitHubRepository(models.Model):
    """Model to store GitHub repository data."""
    
    class RepositoryType(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Private'
        FORK = 'fork', 'Fork'
    
    # Repository identification
    github_id = models.BigIntegerField(unique=True, db_index=True)
    node_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255, db_index=True)
    full_name = models.CharField(max_length=512, unique=True, db_index=True)
    
    # Owner relationship (can be User or Organization)
    owner_username = models.CharField(max_length=100, db_index=True)
    owner_type = models.CharField(max_length=20)  # 'User' or 'Organization'
    
    # Repository metadata
    description = models.TextField(null=True, blank=True)
    homepage = models.URLField(max_length=500, null=True, blank=True)
    html_url = models.URLField(max_length=500)
    
    # Repository type and status
    repo_type = models.CharField(
        max_length=10,
        choices=RepositoryType.choices,
        default=RepositoryType.PUBLIC
    )
    is_fork = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    is_disabled = models.BooleanField(default=False)
    is_template = models.BooleanField(default=False)
    
    # Primary language
    language = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    
    # Topics/tags for discovery
    topics = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True
    )
    
    # Activity metrics
    stargazers_count = models.PositiveIntegerField(default=0, db_index=True)
    watchers_count = models.PositiveIntegerField(default=0)
    forks_count = models.PositiveIntegerField(default=0)
    open_issues_count = models.PositiveIntegerField(default=0)
    
    # Size and activity
    size = models.PositiveIntegerField(default=0)  # in KB
    default_branch = models.CharField(max_length=100, default='main')
    
    # Timestamps
    github_created_at = models.DateTimeField()
    github_updated_at = models.DateTimeField()
    github_pushed_at = models.DateTimeField(null=True, blank=True)
    
    # Our tracking
    fetched_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # License
    license_name = models.CharField(max_length=100, null=True, blank=True)
    license_spdx_id = models.CharField(max_length=50, null=True, blank=True)
    
    # Visibility and permissions
    visibility = models.CharField(max_length=20, default='public')
    has_issues = models.BooleanField(default=True)
    has_projects = models.BooleanField(default=True)
    has_downloads = models.BooleanField(default=True)
    has_wiki = models.BooleanField(default=True)
    has_pages = models.BooleanField(default=False)
    has_discussions = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'GitHub Repository'
        verbose_name_plural = 'GitHub Repositories'
        ordering = ['-stargazers_count', '-forks_count']
        indexes = [
            models.Index(fields=['owner_username']),
            models.Index(fields=['language']),
            models.Index(fields=['-stargazers_count']),
            models.Index(fields=['-github_updated_at']),
            models.Index(fields=['is_fork', '-stargazers_count']),
        ]
    
    def __str__(self):
        return self.full_name
    
    @property
    def popularity_score(self):
        """Calculate a popularity score based on stars, forks, and watchers."""
        import math
        stars = math.log10(self.stargazers_count + 1) * 3
        forks = math.log10(self.forks_count + 1) * 2
        watchers = math.log10(self.watchers_count + 1)
        return round(stars + forks + watchers, 2)
