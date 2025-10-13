import json
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.conf import settings
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.helpers import complete_social_login

class HomeView(TemplateView):
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

@method_decorator(login_required, name='dispatch')
class ProfileView(TemplateView):
    template_name = 'account/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

@csrf_exempt
@require_http_methods(["POST"])
def google_one_tap_auth(request):
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    from allauth.socialaccount.models import SocialApp, SocialAppManager
    from allauth.socialaccount.helpers import complete_social_login
    from django.contrib.auth import login
    from django.conf import settings
    import logging
    import json
    import traceback

    logger = logging.getLogger(__name__)
    
    try:
        # Log the raw request data
        logger.debug(f"Request POST data: {request.POST}")
        
        credential = request.POST.get('credential')
        if not credential:
            logger.error("No credential provided in request")
            return JsonResponse({'error': 'No credential provided'}, status=400)

        logger.debug("Received Google One Tap authentication request")

        # Get the Google OAuth client ID
        try:
            # Try to get the first Google app
            google_apps = SocialApp.objects.filter(provider='google')
            logger.debug(f"Found {len(google_apps)} Google apps")
            
            if not google_apps.exists():
                logger.error("No Google OAuth app is configured in the admin")
                # Try to get client ID from environment as fallback
                client_id = getattr(settings, 'GOOGLE_OAUTH2_CLIENT_ID', None)
                if client_id:
                    logger.info(f"Using client_id from settings: {client_id[:5]}...")
                else:
                    logger.error("GOOGLE_OAUTH2_CLIENT_ID not found in settings")
                    return JsonResponse({
                        'error': 'Google OAuth is not properly configured: No Google app in database and no GOOGLE_OAUTH2_CLIENT_ID in settings',
                        'details': 'Please configure Google OAuth in the admin or set GOOGLE_OAUTH2_CLIENT_ID in settings'
                    }, status=500)
            else:
                google_app = google_apps.first()
                client_id = google_app.client_id
                logger.debug(f"Using Google app: {google_app.name}, client_id: {client_id[:5]}...")
                
                # Log the sites associated with this app
                if hasattr(google_app, 'sites'):
                    site_ids = list(google_app.sites.values_list('id', flat=True))
                    logger.debug(f"Google app is associated with site IDs: {site_ids}")
                
        except Exception as e:
            logger.error(f"Error getting Google OAuth config: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({
                'error': f'Error getting Google OAuth configuration: {str(e)}',
                'details': str(e)
            }, status=500)

        try:
            logger.debug("Verifying Google ID token...")
            # Verify the ID token
            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                client_id
            )
            logger.debug(f"Successfully verified Google ID token. User email: {idinfo.get('email', 'No email')}")
            logger.debug(f"Token info: {json.dumps({k: v for k, v in idinfo.items() if k in ['email', 'name', 'picture']}, indent=2)}")
            
        except ValueError as e:
            logger.error(f"Invalid Google ID token: {str(e)}\nToken: {credential[:100]}...")
            return JsonResponse({
                'error': 'Invalid Google authentication token',
                'details': str(e)
            }, status=400)

        logger.debug("Creating social login...")
        from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
        from allauth.socialaccount.helpers import complete_social_login
        from allauth.socialaccount import providers
        
        try:
            # Get or create the social app
            google_app, created = SocialApp.objects.get_or_create(
                provider='google',
                defaults={
                    'name': 'Google',
                    'client_id': client_id,
                    'secret': getattr(settings, 'GOOGLE_OAUTH2_SECRET', '')
                }
            )
            
            # Ensure the app is associated with the current site
            if not google_app.sites.exists():
                from django.contrib.sites.models import Site
                current_site = Site.objects.get_current()
                google_app.sites.add(current_site)
            
            # Create a social token
            token = SocialToken(
                app=google_app,
                token=credential,
                token_secret='',
                expires_at=None
            )
            
            # Create a social login
            login = providers.registry.by_id('google').sociallogin_from_response(
                request,
                {
                    'id_token': credential,
                    'email': idinfo.get('email'),
                    'name': idinfo.get('name', ''),
                    'given_name': idinfo.get('given_name', ''),
                    'family_name': idinfo.get('family_name', ''),
                    'picture': idinfo.get('picture', '')
                }
            )
            
            # Set the token
            login.token = token
            
            # Complete the login process
            ret = complete_social_login(request, login)
            
            if not ret:
                logger.error("Social login completion failed")
                return JsonResponse({
                    'error': 'Authentication failed: could not complete login'
                }, status=400)

            logger.info("Google One Tap authentication successful")
            return JsonResponse({
                'success': True,
                'redirect': settings.LOGIN_REDIRECT_URL
            })

        except Exception as e:
            logger.exception("Error during social login completion")
            return JsonResponse({
                'error': f'Authentication failed: {str(e)}',
                'details': str(e)
            }, status=500)

    except Exception as e:
        logger.exception("Unexpected error in google_one_tap_auth")
        return JsonResponse({
            'error': 'An unexpected error occurred during authentication'
        }, status=500)
