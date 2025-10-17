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
            is_page = True
        else:
            queryset = queryset_or_page
            is_page = False
            
        # Get the actual model instances if it's a values() queryset
        if hasattr(queryset, 'model') and queryset.model == self.model:
            # Get primary keys of all users in the queryset
            user_ids = list(queryset.values_list('pk', flat=True))
            
            if user_ids:
                # Get stale users from these IDs
                stale_users = list(
                    self.filter(
                        pk__in=user_ids
                    ).filter(
                        models.Q(fetched_at__isnull=True) | 
                        models.Q(fetched_at__lt=timezone.now() - timedelta(hours=24))
                    ).values_list('pk', flat=True)
                )
                
                # Trigger batch update if there are stale users
                if stale_users:
                    from .tasks import update_users_stats_batch
                    update_users_stats_batch.delay(stale_users, "GitHubUser")
        
        return queryset_or_page