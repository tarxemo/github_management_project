# users/managers.py
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

    def update_or_create_from_github(self, github_data, access_token=None):
        """
        Create or update a user from GitHub data.
        """
        github_username = github_data.get('login')
        email = github_data.get('email', '')
        
        if not email:
            email = f"{github_username}@users.noreply.github.com"
        
        defaults = {
            'email': email,
            'first_name': github_data.get('name', '').split(' ')[0],
            'last_name': ' '.join(github_data.get('name', '').split(' ')[1:]),
            'avatar_url': github_data.get('avatar_url', ''),
            'profile_url': github_data.get('html_url', ''),
            'is_active': True,
        }
        
        if access_token:
            defaults['github_access_token'] = access_token
        
        user, created = self.update_or_create(
            github_username=github_username,
            defaults=defaults
        )
        
        return user

    def with_fresh_data(self, queryset=None):
        """
        Ensure all users in the queryset or page have fresh data.
        Returns the same queryset/page for chaining.
        """
        from django.core.paginator import Page
        
        if queryset is None:
            queryset = self.get_queryset()
        
        # Handle both QuerySet and Page objects
        if isinstance(queryset, Page):
            # Get the actual queryset from the page
            user_queryset = queryset.object_list
            # Get the model's base queryset for the filter
            model_queryset = self.get_queryset()
            # Get the pks from the page
            pks = list(user_queryset.values_list('pk', flat=True))
            # Create a new queryset with the same filters but not sliced
            user_queryset = model_queryset.filter(pk__in=pks)
        else:
            # For regular querysets, make sure we're not working with a sliced one
            if not queryset.query.low_mark and not queryset.query.high_mark:
                user_queryset = queryset
            else:
                # If it's already sliced, get the pks and create a new queryset
                pks = list(queryset.values_list('pk', flat=True))
                user_queryset = self.get_queryset().filter(pk__in=pks)
        
        # Identify users that need updates
        stale_users = list(user_queryset.values_list('id', flat=True))
        
        # Trigger batch update if there are stale users
        if stale_users:
            from github_management.tasks import update_users_stats_batch
            update_users_stats_batch.delay(stale_users, "User")
        
        return queryset