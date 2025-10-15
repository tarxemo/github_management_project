# In github_management/managers.py
from django.db import models
from django.utils import timezone
from datetime import timedelta

class GitHubUserManager(models.Manager):
    def with_fresh_data(self, queryset_or_page):
        """
        Ensure all users in the queryset or page have fresh data.
        Returns the same object for chaining.
        """
        from django.core.paginator import Page
        
        # Handle both QuerySet and Page objects
        if isinstance(queryset_or_page, Page):
            queryset = queryset_or_page.object_list
        else:
            queryset = queryset_or_page
            
        # Get the actual model instances if it's a values() queryset
        if hasattr(queryset, 'model'):
            model = queryset.model
            if model and model != self.model:
                # If it's a different model, don't try to update
                return queryset_or_page
                
            # Get the primary keys of users that need updates
            stale_users = list(queryset.filter(
                models.Q(fetched_at__isnull=True) | 
                models.Q(fetched_at__lt=timezone.now() - timedelta(hours=24))
            ).values_list('pk', flat=True))
            
            # Trigger batch update if there are stale users
            if stale_users:
                from .tasks import update_users_stats_batch
                update_users_stats_batch.delay(stale_users)
        
        return queryset_or_page