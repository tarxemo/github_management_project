from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views
from .views_auth import HomeView

app_name = 'github_management'

urlpatterns = [
    # Public pages
    path('', HomeView.as_view(), name='home'),
    
    # Protected pages (require login)
    path('countries/', login_required(views.CountryListView.as_view()), name='country_list'),
    path('countries/<slug:slug>/', login_required(views.CountryDetailView.as_view()), name='country_detail'),
    path('countries/<slug:slug>/fetch/', login_required(views.FetchUsersView.as_view()), name='fetch_users'),
    path('api/countries/<slug:slug>/status/', login_required(views.FetchStatusView.as_view()), name='country_status'),
    
    # Follow/Unfollow functionality
path('follow/', 
     login_required(views.FollowRandomUsersView.as_view()), 
     name='follow_random'),
    path('follow/user/<int:user_id>/', 
         login_required(views.FollowUserView.as_view()), 
         name='follow_user'),
    path('unfollow/', 
         login_required(views.UnfollowNonFollowersView.as_view()), 
         name='unfollow_non_followers'),
    path('update-status/<int:action_id>/', 
         login_required(views.UpdateFollowStatusView.as_view()), 
         name='update_follow_status'),
]