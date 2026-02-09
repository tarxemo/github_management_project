
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from .abstract_models import BaseUser
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .managers import UserManager

class User(AbstractUser, BaseUser):
    username = None  # We're using email as the username
    github_access_token = models.CharField(max_length=255, blank=True, null=True)
    is_internal = models.BooleanField(
        default=False,
        help_text="Designates whether this user is an internal user (registered in our system) or external (just a GitHub user)."
    )
    last_synced_github_followers_following = models.DateTimeField(null=True, blank=True)
    intelligent_follow_enabled = models.BooleanField(
        default=False,
        help_text="Enable intelligent follow/unfollow to boost followers"
    )
    intelligent_follow_schedule = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('manual', 'Manual Only')
        ],
        default='manual',
        help_text="How often to run intelligent follow/unfollow"
    )
    last_intelligent_follow = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Last time the intelligent follow cycle was run"
    )
    # Social & Profile Enhancements
    bio = models.TextField(max_length=500, blank=True, null=True)
    tagline = models.CharField(max_length=160, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    twitter_username = models.CharField(max_length=15, blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    
    class Availability(models.TextChoices):
        OPEN_TO_COLLABORATE = 'collaborate', 'Open to Collaborate'
        HIRING = 'hiring', 'Hiring / Looking for Talent'
        LOOKING_FOR_JOB = 'job', 'Looking for Opportunities'
        LEARNING = 'learning', 'Learning New Things'
        NOT_SPECIFIED = 'none', 'Not Specified'
        
    availability = models.CharField(
        max_length=20,
        choices=Availability.choices,
        default=Availability.NOT_SPECIFIED
    )
    
    # Tech Stack (comma separated or JSON, using JSON for future flexibility)
    preferred_tech_stack = models.JSONField(default=list, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'
        
    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

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
    
    @classmethod
    def get_following(cls, user):
        """Get all users that the given user is following."""
        return cls.objects.filter(from_user=user)
    
    @classmethod
    def get_followers(cls, user):
        """Get all users that are following the given user."""
        return cls.objects.filter(to_user=user)
    