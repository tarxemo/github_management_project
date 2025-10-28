from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views
from .views_auth import HomeView

app_name = 'github_management'

urlpatterns = [
    # Public pages
    path('', HomeView.as_view(), name='home'),
    
    # Protected pages (require login)
    path('countries/', views.CountryListView.as_view(), name='country_list'),
    path('countries/<slug:slug>/', views.CountryDetailView.as_view(), name='country_detail'),
    path('countries/<slug:slug>/update-stats/', views.UpdateCountryUsersStatsView.as_view(), name='country_update_stats'),
    path('countries/<slug:slug>/fetch/', views.FetchUsersView.as_view(), name='fetch_users'),
    path('api/countries/<slug:slug>/status/', views.FetchStatusView.as_view(), name='country_status'),
    
    path('user/<str:github_username>/', 
         views.UserDetailView.as_view(), 
         name='user_detail'),
    path('user/<str:github_username>/refresh/',
         views.UpdateSingleUserStatsView.as_view(),
         name='user_update_stats'),
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
]