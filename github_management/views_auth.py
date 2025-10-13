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
    from allauth.socialaccount.models import SocialLogin, SocialApp
    from allauth.socialaccount.helpers import complete_social_login
    import json

    credential = request.POST.get('credential')
    if not credential:
        return JsonResponse({'error': 'No credential provided'}, status=400)

    try:
        # Get the Google OAuth client ID
        google_app = SocialApp.objects.get(provider='google')
        client_id = google_app.client_id

        # Verify the ID token
        idinfo = id_token.verify_oauth2_token(
            credential,
            requests.Request(),
            client_id
        )

        # Create a social login
        login = SocialLogin()
        login.state = {}
        login.token = {'id_token': credential}
        login.account = {
            'provider': 'google',
            'uid': idinfo['sub'],
            'extra_data': idinfo
        }

        # Complete the login process
        ret = complete_social_login(request, login)
        if not ret:
            return JsonResponse({'error': 'Authentication failed'}, status=400)

        return JsonResponse({
            'success': True,
            'redirect': settings.LOGIN_REDIRECT_URL
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)