# github_management/models_leaderboard.py
from django.db import models
from django.conf import settings
from django.utils import timezone


class Leaderboard(models.Model):
    """Model to store cached leaderboard rankings."""
    
    class LeaderboardType(models.TextChoices):
        GLOBAL = 'global', 'Global'
        COUNTRY = 'country', 'By Country'
        LANGUAGE = 'language', 'By Language'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        FOLLOWERS = 'followers', 'Most Followers'
        CONTRIBUTIONS = 'contributions', 'Most Contributions'
        REPOSITORIES = 'repositories', 'Most Repositories'
        INTELLIGENCE = 'intelligence', 'Intelligence Score'
    
    # Leaderboard identification
    leaderboard_type = models.CharField(
        max_length=20,
        choices=LeaderboardType.choices,
        db_index=True
    )
    
    # Filter criteria (optional, depends on type)
    country_slug = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    language = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    
    # Time period (for weekly/monthly)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    
    # Cached rankings (JSON array of user data)
    rankings = models.JSONField(default=list)
    
    # Metadata
    total_entries = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Cache control
    is_stale = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Leaderboard'
        verbose_name_plural = 'Leaderboards'
        unique_together = ('leaderboard_type', 'country_slug', 'language', 'period_start')
        ordering = ['-last_updated']
        indexes = [
            models.Index(fields=['leaderboard_type', '-last_updated']),
            models.Index(fields=['country_slug', 'leaderboard_type']),
            models.Index(fields=['language', 'leaderboard_type']),
        ]
    
    def __str__(self):
        parts = [self.get_leaderboard_type_display()]
        if self.country_slug:
            parts.append(f"({self.country_slug})")
        if self.language:
            parts.append(f"[{self.language}]")
        return " ".join(parts)
    
    def mark_stale(self):
        """Mark this leaderboard as needing refresh."""
        self.is_stale = True
        self.save(update_fields=['is_stale'])


class LeaderboardEntry(models.Model):
    """Individual entry in a leaderboard for real-time tracking."""
    
    leaderboard = models.ForeignKey(
        Leaderboard,
        on_delete=models.CASCADE,
        related_name='entries'
    )
    
    # User information
    github_username = models.CharField(max_length=100, db_index=True)
    
    # Ranking
    rank = models.PositiveIntegerField(db_index=True)
    score = models.FloatField()  # The metric being ranked
    
    # Additional display data
    display_data = models.JSONField(default=dict)  # Avatar, name, etc.
    
    # Tracking
    previous_rank = models.PositiveIntegerField(null=True, blank=True)
    rank_change = models.IntegerField(default=0)  # Positive = moved up
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Leaderboard Entry'
        verbose_name_plural = 'Leaderboard Entries'
        unique_together = ('leaderboard', 'github_username')
        ordering = ['rank']
        indexes = [
            models.Index(fields=['leaderboard', 'rank']),
            models.Index(fields=['github_username', '-updated_at']),
        ]
    
    def __str__(self):
        return f"#{self.rank} - {self.github_username} ({self.score})"
