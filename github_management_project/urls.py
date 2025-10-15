"""
URL configuration for github_management_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""
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
urlpatterns = [
    path('hidfor/', admin.site.urls),
    
    # GraphQL endpoint
    path("gql/", csrf_exempt(GraphQLView.as_view(graphiql=settings.DEBUG))),
    
    # Allauth URLs for authentication
    path('accounts/', include('allauth.urls')),
    
    # Profile page (requires login)
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # Home page
    path('', HomeView.as_view(), name='home'),
    
    
    path('search/', SearchUsersView.as_view(), name='search_users'),
    # Sitemap
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    
    # Google One Tap authentication
    path('accounts/google/onetap/', google_one_tap_auth, name='google_one_tap_auth'),
    
    # GitHub Management URLs
    path('github/', include(("github_management.urls", "github_management"), namespace="github_management")),
    path('relationships/', include('users.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)