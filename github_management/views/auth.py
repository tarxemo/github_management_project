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
from django.utils import timezone

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
        
        # Add intelligent follow context
        user = self.request.user
        context['can_enable_intelligent'] = bool(user.github_access_token)
        context['intelligent_follow_enabled'] = user.intelligent_follow_enabled
        context['intelligent_follow_schedule'] = user.intelligent_follow_schedule
        context['last_intelligent_follow'] = user.last_intelligent_follow
        
        # Get recent follow actions
        from github_management.models import GitHubFollowAction
        recent_actions = GitHubFollowAction.objects.filter(
            user=user
        ).order_by('-followed_at')[:10]
        context['recent_actions'] = recent_actions
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle intelligent follow settings updates"""
        user = request.user
        
        # Check if user has GitHub token
        if not user.github_access_token:
            return JsonResponse({
                'success': False,
                'message': 'You must add a GitHub access token first to enable intelligent following.'
            })
        
        # Validate GitHub token for intelligent follow
        try:
            from users.validators import validate_github_token_for_intelligent_follow
            validate_github_token_for_intelligent_follow(user.github_access_token)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'GitHub token validation failed: {str(e)}'
            })
        
        action = request.POST.get('action')
        
        if action == 'toggle_intelligent':
            enabled = request.POST.get('enabled') == 'true'
            user.intelligent_follow_enabled = enabled
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': f"Intelligent following {'enabled' if enabled else 'disabled'}"
            })
        
        elif action == 'update_schedule':
            schedule = request.POST.get('schedule')
            if schedule in ['daily', 'weekly', 'manual']:
                user.intelligent_follow_schedule = schedule
                user.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f"Schedule updated to {schedule}"
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid schedule'
                })
        
        elif action == 'run_manual':
            from users.services.intelligent_follow_service import IntelligentFollowService
            from github_management.models import GitHubFollowAction
            
            # Run intelligent follow manually
            result = IntelligentFollowService.intelligent_follow_users(user, max_follows=10)
            
            # Record action - using existing model structure
            from github_management.models import GitHubUser
            # Create or get a placeholder GitHubUser for tracking
            placeholder_user, _ = GitHubUser.objects.get_or_create(
                github_username="manual_run",
                defaults={
                    'country': GitHubUser.objects.first().country if GitHubUser.objects.exists() else None
                }
            )
            GitHubFollowAction.objects.create(
                user=user,
                github_user=placeholder_user,
                status='followed_back' if result['success'] else 'pending'
            )
            
            user.last_intelligent_follow = timezone.now()
            user.save()
            
            return JsonResponse(result)
        
        return JsonResponse({
            'success': False,
            'message': 'Invalid action'
        })


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
        # Ensure app is saved and attached to current site
        if not getattr(google_app, 'pk', None):
            google_app.save()
        current_site = Site.objects.get_current()
        if current_site not in google_app.sites.all():
            google_app.sites.add(current_site)
            google_app.save()
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
        if not social_account.pk:
            social_account.save()

        # Save token
        SocialToken.objects.update_or_create(
            app_id=google_app.id,
            account_id=social_account.id,
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
