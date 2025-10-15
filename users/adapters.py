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
            user.github_username = user.email
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
            user.avatar_url = extra_data.get('avatar_url', '')
            user.profile_url = extra_data.get('html_url', '')
            
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

    def get_app(self, request, provider, client_id=None):
        """Override to handle social app retrieval with better error handling."""
        from allauth.socialaccount.models import SocialApp
        from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
        from django.conf import settings
        
        try:
            # First try to get the app using the parent's method
            try:
                app = super().get_app(request, provider, client_id)
                return app
            except MultipleObjectsReturned:
                # If multiple apps found, try to find the one matching our client_id
                if client_id:
                    app = SocialApp.objects.filter(
                        provider=provider,
                        client_id=client_id
                    ).first()
                    if app:
                        return app
                
                # Otherwise get the first one
                app = SocialApp.objects.filter(provider=provider).first()
                if app:
                    return app
                raise ObjectDoesNotExist("No social app found for provider")
                
        except (ObjectDoesNotExist, MultipleObjectsReturned) as e:
            # If no app found, try to create it from settings
            client_id = getattr(settings, f'{provider.upper()}_OAUTH2_CLIENT_ID', None)
            secret = getattr(settings, f'{provider.upper()}_OAUTH2_SECRET', None)
            
            if client_id and secret:
                app = SocialApp.objects.create(
                    provider=provider,
                    name=provider.capitalize(),
                    client_id=client_id,
                    secret=secret
                )
                # Add current site
                from django.contrib.sites.models import Site
                site = Site.objects.get_current()
                app.sites.add(site)
                app.save()
                return app
                
            # If we can't create the app, raise a more helpful error
            available_providers = list(SocialApp.objects.values_list('provider', flat=True))
            raise Exception(
                f"No {provider} social app found and could not create one. "
                f"Available providers: {available_providers}. "
                f"Please ensure you have configured {provider.upper()}_OAUTH2_CLIENT_ID and {provider.upper()}_OAUTH2_SECRET in your settings."
            )

    def complete_login(self, request, socialapp, token, **kwargs):
        """Handle the completion of a social authentication process."""
        from allauth.socialaccount import app_settings
        from allauth.socialaccount.helpers import complete_social_login
        from allauth.socialaccount.models import SocialLogin
        from allauth.account.utils import get_next_redirect_url
        from django.core.exceptions import ValidationError
        from django.contrib import messages
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Get the provider
            provider = providers.registry.by_id(socialapp.provider, request)
            
            # For Google provider
            if socialapp.provider == 'google':
                response = kwargs.get('response', {})
                
                # Handle One Tap response
                if 'credential' in request.POST:
                    # This is a One Tap response
                    credential = request.POST.get('credential')
                    token.token = credential
                    
                    # Verify the token
                    try:
                        from google.oauth2 import id_token
                        from google.auth.transport import requests as google_requests
                        
                        idinfo = id_token.verify_oauth2_token(
                            credential,
                            google_requests.Request(),
                            socialapp.client_id
                        )
                        
                        # Update response with user info
                        response.update({
                            'id': idinfo.get('sub'),
                            'email': idinfo.get('email'),
                            'name': idinfo.get('name'),
                            'given_name': idinfo.get('given_name'),
                            'family_name': idinfo.get('family_name'),
                            'picture': idinfo.get('picture'),
                            'locale': idinfo.get('locale'),
                        })
                        
                    except Exception as e:
                        logger.error(f"Error verifying Google token: {str(e)}")
                        raise ValidationError("Invalid Google token")
                
                # Handle regular OAuth2 response
                elif 'id_token' in response:
                    token.token_secret = response['id_token']
                
                # Update the token with the response data
                token.token_data = response
                token.save()
                
                # Create social login
                login = provider.sociallogin_from_response(request, response)
                login.token = token
                
                # Ensure the social account is connected to the current site
                if not login.account.pk:
                    login.save(request)
                    
                return login
                
            # For other providers
            return provider.sociallogin_from_response(request, kwargs.get('response', {}))
            
        except Exception as e:
            logger.error(f"Error in complete_login: {str(e)}", exc_info=True)
            messages.error(request, f"Authentication failed: {str(e)}")
            raise