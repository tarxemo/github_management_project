from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from github_management.views_auth import HomeView, ProfileView, google_one_tap_auth
from github_management.sitemap import sitemaps
from github_management.views import SearchUsersView

from django.views.generic.base import TemplateView
from django.http import HttpResponse
from django.conf import settings
import os

# Add this function to serve robots.txt
def robots_txt(request):
    robots_path = os.path.join(settings.STATIC_URL, 'robots.txt')
    try:
        with open(robots_path) as f:
            content = f.read()
        return HttpResponse(content, content_type="text/plain")
    except IOError:
        # Fallback content if robots.txt doesn't exist
        content = """User-agent: *
Allow: /
Sitemap: https://github.tarxemo.com/sitemap.xml

# Disallow admin area
Disallow: /admin/
Disallow: /api/

# Allow media and static files
Allow: /media/
Allow: /static/"""
        return HttpResponse(content, content_type="text/plain")


urlpatterns = [
    path('hidfor/', admin.site.urls),
    
    # Allauth URLs for authentication
    path('accounts/', include('allauth.urls')),
    
    # Profile page (requires login)
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # Home page
    path('', HomeView.as_view(), name='home'),
    
    
    path('search/', SearchUsersView.as_view(), name='opensearch'),
    # Sitemap
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    
    # Google One Tap authentication
    path('accounts/google/onetap/', google_one_tap_auth, name='google_one_tap_auth'),
    
    # GitHub Management URLs
    path('github/', include(("github_management.urls", "github_management"), namespace="github_management")),
    path('relationships/', include('users.urls')),
    path('robots.txt', robots_txt, name='robots'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

