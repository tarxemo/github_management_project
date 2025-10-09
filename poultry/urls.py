"""
URL configuration for poultry project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from github_management.views_auth import HomeView, ProfileView

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
    
    # GitHub Management URLs
    path('github/', include(("github_management.urls", "github_management"), namespace="github_management")),
]

