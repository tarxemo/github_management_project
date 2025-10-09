from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Remove username field and use email as the unique identifier
    username = None
    email = models.EmailField(unique=True)
    
    # GitHub specific fields
    github_username = models.CharField(max_length=100, blank=True, null=True)
    github_avatar_url = models.URLField(max_length=255, blank=True, null=True)
    github_profile_url = models.URLField(max_length=255, blank=True, null=True)
    github_access_token = models.CharField(max_length=255, blank=True, null=True)
    
    # Use email as the username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email
