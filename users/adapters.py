# users/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        """
        Saves a new [User](cci:2://file:///media/tarxemo/TarXemo/GT/RB/users/models.py:3:0-22:74) instance using information provided in the
        signup form.
        """
        user = super().save_user(request, user, form, commit=commit)
        return user

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def __init__(self, request=None):
        super().__init__(request)
        self.account_adapter = CustomAccountAdapter(request)
    
    def is_open_for_signup(self, request, sociallogin):
        """
        Override to allow social signups.
        """
        return True

    def populate_username(self, request, user):
        """
        Populate username from social login.
        """
        if hasattr(user, 'email') and user.email:
            user.username = user.email
        return user

    def new_user(self, request, sociallogin):
        """
        Create a new user instance.
        """
        user = self.account_adapter.new_user(request)
        user.set_unusable_password()
        return user

    def populate_user(self, request, sociallogin, data):
        """
        Populate user information from social provider info.
        """
        user = super().populate_user(request, sociallogin, data)
        
        if sociallogin.account.provider == 'github':
            extra_data = sociallogin.account.extra_data
            
            # Set GitHub specific fields
            user.github_username = extra_data.get('login', '')
            user.github_avatar_url = extra_data.get('avatar_url', '')
            user.github_profile_url = extra_data.get('html_url', '')
            
            # Set email from GitHub if not already set
            if not user.email and 'email' in extra_data:
                user.email = extra_data['email']
            
            # Set name from GitHub if not already set
            if not user.first_name and 'name' in extra_data:
                name = extra_data['name']
                if name:
                    name_parts = name.split(' ', 1)
                    user.first_name = name_parts[0]
                    if len(name_parts) > 1:
                        user.last_name = name_parts[1]
            
            # If we still don't have a name, use the GitHub username
            if not user.first_name and 'login' in extra_data:
                user.first_name = extra_data['login']
        
        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login.
        """
        user = super().save_user(request, sociallogin, form=form)
        if not user.has_usable_password():
            user.set_unusable_password()
            user.save()
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        """
        Returns the default URL to redirect to after successfully connecting
        a social account.
        """
        return '/profile/'
        
    def clean_email(self, email):
        """
        Validates an email value.
        """
        if not email:
            return None
        return email.lower()