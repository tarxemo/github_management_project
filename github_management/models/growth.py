# github_management/models_growth.py
from django.db import models
from django.conf import settings
from django.utils import timezone


class GrowthAnalytics(models.Model):
    """Daily snapshots of user growth metrics."""
    
    github_username = models.CharField(max_length=100, db_index=True)
    date = models.DateField(default=timezone.now, db_index=True)
    
    # Core Metrics
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    public_repos_count = models.PositiveIntegerField(default=0)
    contributions_count = models.PositiveIntegerField(default=0)
    stars_received_count = models.PositiveIntegerField(default=0)
    
    # Delta (change from previous snapshot)
    followers_delta = models.IntegerField(default=0)
    stars_delta = models.IntegerField(default=0)
    contributions_delta = models.IntegerField(default=0)
    
    # Derived Metrics
    engagement_rate = models.FloatField(default=0.0)  # stars / followers or similar
    
    class Meta:
        verbose_name = 'Growth Analytics'
        verbose_name_plural = 'Growth Analytics Snapshots'
        unique_together = ('github_username', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['github_username', '-date']),
        ]
    
    def __str__(self):
        return f"{self.github_username} - {self.date}"
