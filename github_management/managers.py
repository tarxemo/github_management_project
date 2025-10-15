# In github_management/managers.py
from django.db import models
from django.utils import timezone
from datetime import timedelta

class GitHubUserManager(models.Manager):
    def with_fresh_data(self, queryset=None):
        """
        Ensure all users in the queryset have fresh data.
        Returns the same queryset for chaining.
        """
        if queryset is None:
            queryset = self.get_queryset()
            
        # Identify users that need updates
        stale_users = list(queryset.filter(
            models.Q(fetched_at__isnull=True) | 
            models.Q(fetched_at__lt=timezone.now() - timedelta(hours=24))
        ).values_list('username', flat=True))
        
        # Trigger batch update if there are stale users
        if stale_users:
            from .tasks import update_users_stats_batch
            update_users_stats_batch.delay(stale_users)
            
        return queryset