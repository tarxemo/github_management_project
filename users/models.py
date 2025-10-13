
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _



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



class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    
    # GitHub specific fields
    github_username = models.CharField(max_length=100, blank=True, null=True)
    github_avatar_url = models.URLField(max_length=255, blank=True, null=True)
    github_profile_url = models.URLField(max_length=255, blank=True, null=True)
    github_access_token = models.CharField(max_length=255, blank=True, null=True)
    
    is_internal = models.BooleanField(
        default=False,
        help_text="Designates whether this user is an internal user (registered in our system) or external (just a GitHub user)."
    )
    
    objects = CustomUserManager()
    
    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email
    
    def _update_relationship_status(self, relationship, other_relationship_exists):
        """Helper method to update relationship status to mutual if needed"""
        if other_relationship_exists:
            relationship.relationship_type = UserFollowing.RelationshipType.MUTUAL
            relationship.save()
            return relationship
        return relationship



    def save(self, *args, **kwargs):
        created = not self.pk
        super().save(*args, **kwargs)
        
        # If user has GitHub info, try to sync followers/following
        if self.github_access_token:
            try:
                from users.tasks import sync_github_followers_following
                sync_github_followers_following.delay(self.id)
            except Exception as e:
                # Log the error but don't fail the save operation
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error scheduling GitHub sync for user {self.id}: {str(e)}", exc_info=True)
                
class UserFollowing(models.Model):
    """Through model for the many-to-many relationship between users."""
    
    class RelationshipStatus(models.TextChoices):
        FOLLOWING = 'following', 'Following'
        # Removed MUTUAL status as it's redundant
    
    from_user = models.ForeignKey(
        User,
        related_name='following_relationships',
        on_delete=models.CASCADE,
        help_text='The user who is following'
    )
    
    to_user = models.ForeignKey(
        User,
        related_name='follower_relationships',
        on_delete=models.CASCADE,
        help_text='The user being followed'
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
    
