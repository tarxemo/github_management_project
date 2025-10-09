from django.dispatch import receiver
from allauth.socialaccount.signals import social_account_added

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
        user.save()
