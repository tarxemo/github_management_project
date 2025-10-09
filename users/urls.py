# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('relationships/', views.relationship_management, name='relationship_management'),
    path('follow/<str:username>/', views.follow_user, name='follow_user'),
    path('unfollow/<str:username>/', views.unfollow_user, name='unfollow_user'),
    path('api/relationship-stats/', views.relationship_stats, name='relationship_stats'),
    path('add-github-token/', views.add_github_token, name='add_github_token'),
]