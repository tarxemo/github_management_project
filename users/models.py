
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from .abstract_models import BaseUser
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

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

class User(AbstractUser, BaseUser):
    username = None  # This tells Django to use email as the username
    github_access_token = models.CharField(max_length=255, blank=True, null=True)
    is_internal = models.BooleanField(
        default=False,
        help_text="Designates whether this user is an internal user (registered in our system) or external (just a GitHub user)."
    )
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'
        
    def __str__(self):
        return f"{self.email} ({self.github_username or 'no GitHub'})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

class UserFollowing(models.Model):
    """Through model for the many-to-many relationship between users."""
    
    class RelationshipStatus(models.TextChoices):
        FOLLOWING = 'following', 'Following'
        # Removed MUTUAL status as it's redundant
    
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='following_relationships',
        on_delete=models.CASCADE
    )
    
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='follower_relationships',
        on_delete=models.CASCADE
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['from_user']),
            models.Index(fields=['to_user']),
            models.Index(fields=['from_user', 'to_user']),  # For faster lookups
        ]
    
    def __str__(self):
        return f"{self.from_user} follows {self.to_user}"
    
    @classmethod
    def follow(cls, from_user, to_user):
        """Follow another user."""
        if not from_user or not to_user or from_user == to_user:
            return None
            
        # Use get_or_create to handle race conditions
        relationship, created = cls.objects.get_or_create(
            from_user=from_user,
            to_user=to_user
        )
        return relationship
    
    @classmethod
    def get_relationship(cls, user1, user2):
        """Get the relationship between two users."""
        if not user1 or not user2 or user1 == user2:
            return None
            
        try:
            return cls.objects.get(
                from_user=user1,
                to_user=user2
            )
        except cls.DoesNotExist:
            return None
    
