# users/signals.py
from django.dispatch import receiver
from allauth.socialaccount.signals import social_account_added
from django.db.models.signals import post_save
from .models import User, UserFollowing

@receiver(social_account_added)
def update_user_social_data(request, sociallogin, **kwargs):
    """
    Update user data when a new social account is added.
    """
    user = sociallogin.user
    extra_data = sociallogin.account.extra_data
    
    if sociallogin.account.provider == 'github':
        user.github_username = extra_data.get('login', '')
        user.github_avatar_url = extra_data.get('avatar_url', '')
        user.github_profile_url = extra_data.get('html_url', '')
        user.is_internal = True  # Mark as internal user
        user.save()

@receiver(post_save, sender=User)
def convert_external_to_internal(sender, instance, created, **kwargs):
    """
    When a user registers, convert any existing relationships where they were an external user.
    """
    if created and instance.is_internal and instance.github_username:
        # Find any relationships where this user was followed as an external user
        from_relationships = UserFollowing.objects.filter(
            to_user__github_username__iexact=instance.github_username,
            to_user__is_internal=False
        )
        
        for rel in from_relationships:
            # Update the relationship to point to the internal user
            rel.to_user = instance
            rel.save()
            
            # If this creates a mutual relationship, update the reverse
            reverse_rel = UserFollowing.objects.filter(
                from_user=instance,
                to_user=rel.from_user
            ).first()
            
            if reverse_rel:
                # Both users follow each other
                pass  # The relationship is already mutual by design