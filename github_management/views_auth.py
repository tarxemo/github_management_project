import json
import logging
import traceback
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.conf import settings
from django.contrib.sites.models import Site

from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialLogin

# Initialize logger
logger = logging.getLogger(__name__)


# -------------------- HOME VIEW --------------------
class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


# -------------------- PROFILE VIEW --------------------
@method_decorator(login_required, name='dispatch')
class ProfileView(TemplateView):
    template_name = 'account/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


# -------------------- GOOGLE ONE TAP AUTH --------------------
@csrf_exempt
@require_http_methods(["POST"])
def google_one_tap_auth(request):
    """
    Handle Google One Tap authentication.
    """
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    from allauth.socialaccount import providers

    try:
        logger.debug(f"Incoming POST data: {request.POST}")

        credential = request.POST.get('credential')
        if not credential:
            logger.error("Missing 'credential' in request.")
            return JsonResponse({'error': 'No credential provided'}, status=400)

        # Retrieve Google OAuth client ID
        try:
            google_app = SocialApp.objects.filter(provider='google').first()
            if google_app:
                client_id = google_app.client_id
                logger.debug(f"Using Google app: {google_app.name} ({client_id[:8]}...)")
            else:
                client_id = getattr(settings, 'GOOGLE_OAUTH2_CLIENT_ID', None)
                if not client_id:
                    logger.error("No Google OAuth client ID found.")
                    return JsonResponse({
                        'error': 'Google OAuth is not configured properly',
                        'details': 'Missing SocialApp or GOOGLE_OAUTH2_CLIENT_ID in settings'
                    }, status=500)
        except Exception as e:
            logger.error(f"Error retrieving Google OAuth app: {str(e)}\n{traceback.format_exc()}")
            return JsonResponse({'error': 'Failed to get Google OAuth configuration', 'details': str(e)}, status=500)

        # Verify the Google token
        try:
            idinfo = id_token.verify_oauth2_token(
                credential, google_requests.Request(), client_id
            )
            logger.debug(f"Token verified. Google user: {idinfo.get('email', 'N/A')}")
        except ValueError as e:
            logger.error(f"Invalid Google ID token: {str(e)}")
            return JsonResponse({'error': 'Invalid Google ID token', 'details': str(e)}, status=400)

        # Create or get SocialApp entry
        google_app, _ = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': client_id,
                'secret': getattr(settings, 'GOOGLE_OAUTH2_SECRET', '')
            }
        )

        # Associate app with current site if needed
        if not google_app.sites.exists():
            current_site = Site.objects.get_current()
            google_app.sites.add(current_site)
            logger.debug(f"Associated Google app with site: {current_site.domain}")

        # Create the SocialAccount instance
        social_account = SocialAccount(
            provider='google',
            uid=idinfo.get('sub'),
            extra_data={
                'email': idinfo.get('email'),
                'name': idinfo.get('name', ''),
                'given_name': idinfo.get('given_name', ''),
                'family_name': idinfo.get('family_name', ''),
                'picture': idinfo.get('picture', ''),
            },
        )

        # Create the token and link it to the account
        token = SocialToken(app=google_app, token=credential, account=social_account)

        # Build the SocialLogin object
        social_login = SocialLogin(account=social_account, token=token)


        # Complete social login
        response = complete_social_login(request, social_login)

        # Determine redirect
        redirect_url = getattr(settings, 'LOGIN_REDIRECT_URL', '/')
        if hasattr(response, 'url') and response.url:
            redirect_url = response.url

        logger.info(f"✅ Google One Tap authentication successful for {idinfo.get('email')}")
        return JsonResponse({'success': True, 'redirect': redirect_url})

    except Exception as e:
        logger.exception("Unhandled error during Google One Tap authentication")
        return JsonResponse({
            'error': 'Authentication failed',
            'details': str(e),
            'traceback': traceback.format_exc() if settings.DEBUG else None
        }, status=500)
