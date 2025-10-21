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
from allauth.socialaccount.adapter import get_adapter as get_social_adapter
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
from django.contrib.auth import login, get_user_model
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken

User = get_user_model()

@csrf_exempt
def google_one_tap_auth(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Only POST method allowed"}, status=405)

        # Parse credential
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

        # Verify token via Google
        try:
            adapter = get_social_adapter(request)
            google_app = adapter.get_app(request, 'google')
        except Exception as e:
            return JsonResponse({
                "error": "Authentication failed",
                "details": str(e)
            }, status=500)
        token_info = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
        ).json()

        if "error_description" in token_info:
            return JsonResponse({
                "error": "Invalid token",
                "details": token_info
            }, status=400)

        email = token_info.get("email")
        name = token_info.get("name", email.split("@")[0])

        if not email:
            return JsonResponse({"error": "Email not provided by Google"}, status=400)

        # Build defaults safely for custom user model
        defaults = {}
        if hasattr(User, "email"):
            defaults["email"] = email
        if hasattr(User, "first_name"):
            defaults["first_name"] = token_info.get("given_name", "example")
        if hasattr(User, "last_name"):
            defaults["last_name"] = token_info.get("family_name", "example")

        user, created = User.objects.get_or_create(email=email, defaults=defaults)

        # Create or link social account
        social_account, _ = SocialAccount.objects.get_or_create(
            user=user,
            provider='google',
            uid=token_info.get("sub"),
            defaults={"extra_data": token_info},
        )

        # Save token
        SocialToken.objects.update_or_create(
            app=google_app,
            account=social_account,
            defaults={"token": credential}
        )

        # ✅ Log in user with explicit backend
        login(request, user, backend="allauth.account.auth_backends.AuthenticationBackend")

        return JsonResponse({
            "success": True,
            "user": {
                "email": user.email,
                "created": created,
                "name": getattr(user, "first_name", name)
            }
        })

    except Exception as e:
        import traceback
        return JsonResponse({
            "error": "Authentication failed",
            "details": str(e),
            "traceback": traceback.format_exc()
        }, status=500)
