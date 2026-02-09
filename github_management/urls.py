from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import core as views
from .views.auth import HomeView
from .views.leaderboard_view import LeaderboardView
from .views.analytics_view import AnalyticsDashboardView
from .views.discovery_view import DiscoveryFeedView

app_name = 'github_management'

urlpatterns = [
    # Public pages
    path('', HomeView.as_view(), name='home'),
    
    # Protected pages (require login)
    path('countries/', views.CountryListView.as_view(), name='country_list'),
    path('countries/<slug:slug>/', views.CountryDetailView.as_view(), name='country_detail'),
    path('countries/<slug:slug>/update-stats/', views.UpdateCountryUsersStatsView.as_view(), name='country_update_stats'),
    path('countries/<slug:slug>/recompute-ranking/', views.RecomputeCountryRankingView.as_view(), name='country_recompute_ranking'),
    path('countries/<slug:slug>/fetch/', views.FetchUsersView.as_view(), name='fetch_users'),
    path('api/countries/<slug:slug>/status/', views.FetchStatusView.as_view(), name='country_status'),
    
    path('user/<str:github_username>/', 
         views.UserDetailView.as_view(), 
         name='user_detail'),
    path('user/<str:github_username>/refresh/',
         views.UpdateSingleUserStatsView.as_view(),
         name='user_update_stats'),
    path('user/<str:github_username>/star-repos/',
         views.StarUserReposView.as_view(),
         name='user_star_repos'),
         
    # Follow/Unfollow functionality
    path('follow/', 
         views.FollowRandomUsersView.as_view(), 
         name='follow_random'),
    path('follow_user/<int:user_id>/', 
         views.FollowUserView.as_view(), 
         name='follow_user'),
    path('unfollow/', 
         views.UnfollowNonFollowersView.as_view(), 
         name='unfollow_non_followers'),
    path('update-status/<int:action_id>/', 
         views.UpdateFollowStatusView.as_view(), 
         name='update_follow_status'),
         
    path('fetch-all-countries/', 
         login_required(views.FetchAllCountriesView.as_view()), 
         name='fetch_all_countries'),
    path('recompute-all-countries-ranking/',
         login_required(views.RecomputeAllCountriesRankingView.as_view()),
         name='recompute_all_countries_ranking'),
    
    # Phase 6 Features
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('analytics/', AnalyticsDashboardView.as_view(), name='analytics'),
    path('discovery/', DiscoveryFeedView.as_view(), name='discovery'),
]
