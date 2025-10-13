from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount import providers
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=commit)
        return user

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def __init__(self, request=None):
        super().__init__(request)
        self.account_adapter = CustomAccountAdapter(request)
    
    def is_open_for_signup(self, request, sociallogin):
        return True

    def populate_username(self, request, user):
        if hasattr(user, 'email') and user.email:
            user.username = user.email
        return user

    def new_user(self, request, sociallogin):
        user = self.account_adapter.new_user(request)
        user.set_unusable_password()
        return user

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        
        if sociallogin.account.provider == 'github':
            extra_data = sociallogin.account.extra_data
            user.github_username = extra_data.get('login', '')
            user.github_avatar_url = extra_data.get('avatar_url', '')
            user.github_profile_url = extra_data.get('html_url', '')
            
            if not user.email and 'email' in extra_data:
                user.email = extra_data['email']
            
            if not user.first_name and 'name' in extra_data:
                name = extra_data['name']
                if name:
                    name_parts = name.split(' ', 1)
                    user.first_name = name_parts[0]
                    if len(name_parts) > 1:
                        user.last_name = name_parts[1]
            
            if not user.first_name and 'login' in extra_data:
                user.first_name = extra_data['login']
        
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        if not user.has_usable_password():
            user.set_unusable_password()
            user.save()
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        return '/profile/'
        
    def clean_email(self, email):
        if not email:
            return None
        return email.lower()

    def complete_login(self, request, socialapp, token, **kwargs):
        """
        Handle the completion of a social authentication process.
        """
        # For Google One Tap, we need to handle the id_token specially
        if socialapp.provider == 'google' and 'id_token' in kwargs.get('response', {}):
            # Store the id_token in the token's token_secret field
            token.token_secret = kwargs['response']['id_token']
        
        # Get the provider and complete the login
        provider = providers.registry.by_id(socialapp.provider, request)
        return provider.sociallogin_from_response(request, kwargs.get('response', {}))