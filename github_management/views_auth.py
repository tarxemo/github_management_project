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
    from google.auth.transport import requests
    from allauth.socialaccount.models import SocialApp
    from allauth.socialaccount.helpers import complete_social_login
    from django.contrib.auth import login
    import logging
    import json

    logger = logging.getLogger(__name__)
    
    try:
        credential = request.POST.get('credential')
        if not credential:
            logger.error("No credential provided in request")
            return JsonResponse({'error': 'No credential provided'}, status=400)

        logger.debug("Received Google One Tap authentication request")

        # Get the Google OAuth client ID
        try:
            google_app = SocialApp.objects.get(provider='google')
            client_id = google_app.client_id
            logger.debug(f"Found Google app with client_id: {client_id[:5]}...")
        except SocialApp.DoesNotExist:
            logger.error("Google OAuth app is not configured in the admin")
            return JsonResponse({
                'error': 'Google OAuth is not properly configured'
            }, status=500)

        try:
            # Verify the ID token
            idinfo = id_token.verify_oauth2_token(
                credential,
                requests.Request(),
                client_id
            )
            logger.debug("Successfully verified Google ID token")
        except ValueError as e:
            logger.error(f"Invalid Google ID token: {str(e)}")
            return JsonResponse({
                'error': 'Invalid Google authentication token'
            }, status=400)

        # Create a social login
        from allauth.socialaccount.models import SocialLogin
        from allauth.socialaccount.models import SocialToken
        from allauth.socialaccount.adapter import get_adapter
        
        try:
            login = get_adapter().complete_login(
                request,
                None,  # socialapp
                None,  # token
                response={'id_token': credential}
            )
            login.token = SocialToken(
                app=google_app,
                token=credential,
                token_secret=''
            )
            
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
                'error': f'Authentication failed: {str(e)}'
            }, status=500)

    except Exception as e:
        logger.exception("Unexpected error in google_one_tap_auth")
        return JsonResponse({
            'error': 'An unexpected error occurred during authentication'
        }, status=500)
