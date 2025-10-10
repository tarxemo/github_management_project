from django.conf import settings

def google_auth(request):
    """Add Google OAuth client ID to template context."""
    return {
        'GOOGLE_OAUTH2_CLIENT_ID': getattr(settings, 'GOOGLE_OAUTH2_CLIENT_ID', '')
    }
