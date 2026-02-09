from django.db import models
from django.conf import settings
from django.utils import timezone

class Achievement(models.Model):
    """Definition of an achievement that can be earned by users."""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField()
    icon_name = models.CharField(max_length=50, help_text="Lucide icon name or CSS class")
    points = models.PositiveIntegerField(default=10)
    
    class Tier(models.TextChoices):
        BRONZE = 'bronze', 'Bronze'
        SILVER = 'silver', 'Silver'
        GOLD = 'gold', 'Gold'
        PLATINUM = 'platinum', 'Platinum'
        DIAMOND = 'diamond', 'Diamond'
        
    tier = models.CharField(
        max_length=20,
        choices=Tier.choices,
        default=Tier.BRONZE
    )
    
    # Conditions (simplified for now, logic will be in services)
    condition_type = models.CharField(max_length=50, help_text="e.g., 'followers_count', 'contributions'")
    condition_value = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['points']

    def __str__(self):
        return f"{self.name} ({self.tier})"

class UserAchievement(models.Model):
    """Relationship between a User and an Achievement they've earned."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='achievements'
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name='earned_by'
    )
    earned_at = models.DateTimeField(default=timezone.now)
    
    # For tiered achievements that might have progress
    current_progress = models.IntegerField(default=0)
    is_unlocked = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('user', 'achievement')
        ordering = ['-earned_at']

    def __str__(self):
        return f"{self.user} - {self.achievement}"
