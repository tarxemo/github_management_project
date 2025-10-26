from django.urls import path
from .views import github_badge

app_name = 'badges'

urlpatterns = [
    # /badges/github/<username>/<badge_type>/
    path('badges/<str:username>/<str:badge_type>/', github_badge, name='github_badge'),
]
