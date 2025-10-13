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


import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from allauth.socialaccount.models import SocialLogin
from django.contrib.auth import get_user_model

User = get_user_model()

@csrf_exempt
def google_one_tap_auth(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Only POST method allowed"}, status=405)

        # Handle both JSON and form requests
        try:
            if request.body:
                body = json.loads(request.body.decode("utf-8"))
                credential = body.get("credential")
            else:
                credential = request.POST.get("credential")
        except json.JSONDecodeError:
            credential = request.POST.get("credential")

        if not credential:
            return JsonResponse({"error": "Missing credential"}, status=400)

        # Verify token with Google
        google_app = SocialApp.objects.get(provider='google')
        token_info = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
        ).json()

        if "error_description" in token_info:
            return JsonResponse({"error": "Invalid token", "details": token_info}, status=400)

        email = token_info.get("email")
        name = token_info.get("name", email.split("@")[0])

        if not email:
            return JsonResponse({"error": "Email not provided by Google"}, status=400)

        # Create or get user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": name}
        )

        # Create or update social account
        social_account, _ = SocialAccount.objects.get_or_create(
            user=user,
            provider='google',
            uid=token_info.get("sub"),
            defaults={"extra_data": token_info},
        )

        # Store or refresh token
        social_token, _ = SocialToken.objects.update_or_create(
            app=google_app,
            account=social_account,
            defaults={"token": credential}
        )

        # ✅ Log in the user directly (no allauth flow)
        login(request, user)

        return JsonResponse({
            "success": True,
            "user": {
                "email": user.email,
                "username": user.username,
                "created": created
            }
        })

    except Exception as e:
        import traceback
        return JsonResponse({
            "error": "Authentication failed",
            "details": str(e),
            "traceback": traceback.format_exc()
        }, status=500)
