# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction, models
from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import timedelta
import random
import logging
from .models import Country, GitHubUser, GitHubFollowAction
from users.models import UserFollowing
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import View
from .tasks import fetch_all_countries_users
from django.urls import reverse

logger = logging.getLogger(__name__)

from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

class CountryListView( ListView):
    """View to list all available countries with search and pagination"""
    model = Country
    template_name = 'github_management/country_list.html'
    context_object_name = 'countries'
    paginate_by = 20
    ordering = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('q', '').strip()
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) 
            )
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['active_tab'] = 'countries'
        return context

class FetchAllCountriesView(View):
    """View to trigger fetching users for all countries"""
    
    def get(self, request, *args, **kwargs):
        if request.user.is_superuser:
            task = fetch_all_countries_users.delay()
            messages.success(
                request,
                f"Started fetching users for all countries. Task ID: {task.id}"
            )
        else:
            messages.error(request, "You do not have permission to perform this action.")
        return redirect('github_management:country_list')
    
class CountryDetailView(View):
    """View to show users for a specific country"""
    def get(self, request, slug):
        country = get_object_or_404(Country, slug=slug)
        
        # Get users for this country
        users = GitHubUser.objects.filter(country=country).order_by('-contributions_last_year')
        
        # Pagination
        paginator = Paginator(users, 25)  # Show 25 users per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        GitHubUser.objects.with_fresh_data(page_obj)
        return render(request, 'github_management/country_detail.html', {
            'country': country,
            'page_obj': page_obj,
            'active_tab': 'countries'
        })

class FetchUsersView(View):
    """View to trigger user fetching for a country"""
    def post(self, request, slug):
        country = get_object_or_404(Country, slug=slug)
        
        if country.is_fetching:
            messages.warning(request, f"Users for {country.name} are already being fetched. Please wait.")
            return redirect('github_management:country_detail', slug=slug)
            
        # Mark as fetching
        country.is_fetching = True
        country.save()
        
        try:
            # Import here to avoid circular imports
            from .tasks import fetch_users_for_country
            fetch_users_for_country.delay(country.id)
            messages.success(request, f"Started fetching users for {country.name}. This may take a while...")
        except Exception as e:
            logger.error(f"Error starting user fetch for {country.name}: {e}")
            country.is_fetching = False
            country.save()
            messages.error(request, f"Failed to start fetching users: {str(e)}")
            
        return redirect('github_management:country_detail', slug=slug)

class FetchStatusView(View):
    """API endpoint to check fetch status"""
    def get(self, request, slug):
        country = get_object_or_404(Country, slug=slug)
        return JsonResponse({
            'is_fetching': country.is_fetching,
            'last_updated': country.last_updated.isoformat() if country.last_updated else None,
            'user_count': country.user_count
        })

class FollowRandomUsersView(View):
    """View to follow random users from any country"""
    def get(self, request):
        # Get users not already followed by the current user, ordered randomly
        users_to_follow = GitHubUser.objects.exclude(
            follow_actions__user=request.user
        ).select_related('country').order_by('?')[:50]  # Show first 50 random users
        
        # Get all countries for the filter dropdown
        countries = Country.objects.all().order_by('name')
        GitHubUser.objects.with_fresh_data(users_to_follow)
        # Get the most common country from the users to follow (for display purposes)
        country = users_to_follow[0].country.name if users_to_follow else None
        
        return render(request, 'github_management/follow_random.html', {
            'country': country,
            'countries': countries,
            'users': users_to_follow,
            'active_tab': 'follow'
        })
    
    def post(self, request):
        if not request.user.is_authenticated:
            login_url = reverse('account_login')
            messages.error(request, f"You need to login first. Prefer GitHub login. Go to {login_url}")
            return redirect('github_management:follow_random')
        # Token check
        if not getattr(request.user, 'github_access_token', None):
            add_token_url = reverse('add_github_token')
            messages.error(request, f"GitHub token required to follow users. Add one here: {add_token_url}")
            return redirect('github_management:follow_random')
        
        count = int(request.POST.get('count', 10))  # Default to 10 users
        country_id = request.POST.get('country')
        
        # Build the base query
        users_query = GitHubUser.objects.exclude(
            follow_actions__user=request.user
        )
        
        # Filter by country if specified
        if country_id:
            users_query = users_query.filter(country_id=country_id)
            country = get_object_or_404(Country, id=country_id)
            country_name = country.name
        else:
            country_name = "all countries"
        
        # Get random users
        users_to_follow = list(users_query.order_by('?')[:count])
        
        # Follow each user
        followed = 0
        for user in users_to_follow:
            try:
                GitHubFollowAction.follow_github_user(request.user, user)
                followed += 1
            except Exception as e:
                logger.error(f"Error following user {user.github_username}: {e}")
        
        messages.success(
            request, 
            f"Started following {followed} new users from {country_name}."
        )
        return redirect('github_management:follow_random')
    
    
class FollowUserView(View):
    """API endpoint to follow a specific GitHub user"""
    def post(self, request, user_id):
        if not request.user.is_authenticated:
            login_url = reverse('account_login')
            return JsonResponse({
                'success': False,
                'message': 'You need to login first. Prefer GitHub login.',
                'login_url': login_url
            }, status=401)

        # Token check
        if not getattr(request.user, 'github_access_token', None):
            add_token_url = reverse('add_github_token')
            return JsonResponse({
                'success': False,
                'message': 'GitHub token missing. Please add your token to proceed.',
                'add_token_url': add_token_url
            }, status=400)
            
        github_user = get_object_or_404(GitHubUser, id=user_id)
        
        try:
            follow_action = GitHubFollowAction.follow_github_user(request.user, github_user)
            return JsonResponse({
                'success': True,
                'message': f'Started following {github_user.github_username}',
                'action_id': follow_action.id
            })
        except Exception as e:
            logger.error(f"Error following user {github_user.github_username}: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Failed to follow user: {str(e)}'
            }, status=400)


class UnfollowNonFollowersView(View):
    """View to unfollow users who haven't followed back"""
    def get(self, request):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to unfollow users.")
            return redirect('github_management:unfollow_non_followers')
        
        # Get pending follow actions that haven't been followed back
        pending_actions = GitHubFollowAction.objects.filter(
            user=request.user,
            status=GitHubFollowAction.FollowStatus.PENDING
        ).select_related('github_user').order_by('-followed_at')
        
        return render(request, 'github_management/unfollow_non_followers.html', {
            'pending_actions': pending_actions,
            'active_tab': 'unfollow'
        })
    
    def post(self, request):
        days = int(request.POST.get('days', 3))  # Default to 3 days
        
        try:
            unfollowed_count = GitHubFollowAction.unfollow_non_followers(request.user, days)
            messages.success(request, f"Unfollowed {unfollowed_count} users who didn't follow you back after {days} days.")
        except Exception as e:
            logger.error(f"Error unfollowing non-followers: {e}")
            messages.error(request, f"Failed to unfollow users: {str(e)}")
        
        return redirect('github_management:unfollow_non_followers')


class UpdateFollowStatusView(View):
    """API endpoint to update follow status for a user"""
    def post(self, request, action_id):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to update follow status.")
            return JsonResponse({
                'success': False,
                'message': 'You must be logged in to update follow status.'
            }, status=401)
        
        try:
            action = GitHubFollowAction.objects.get(
                id=action_id,
                user=request.user
            )
            status = action.update_follow_status()
            
            return JsonResponse({
                'success': True,
                'status': status,
                'status_display': action.get_status_display(),
                'last_checked': action.last_checked.strftime('%Y-%m-%d %H:%M') if action.last_checked else None
            })
        except GitHubFollowAction.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Follow action not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error updating follow status {action_id}: {e}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)

class UserDetailView(View):
    """View to show detailed information about a GitHub user"""
    def get(self, request, github_username):
        user = get_object_or_404(GitHubUser, github_username__iexact=github_username)
        
        # Check if the current user is following this GitHub user
        # Only check if the user is authenticated
        is_following = False
        if request.user.is_authenticated:
            is_following = GitHubFollowAction.objects.filter(
                user=request.user,
                github_user=user
            ).exists()
        
        # Get similar users from the same country
        similar_users = GitHubUser.objects.filter(
            country=user.country
        ).exclude(id=user.id).order_by('-contributions_last_year')[:5]
        GitHubUser.objects.with_fresh_data(similar_users)
        
        context = {
            'github_user': user,
            'is_following': is_following,
            'similar_users': similar_users,
            'active_tab': 'users',
        }
        
        return render(request, 'github_management/user_detail.html', context)

    

class SearchUsersView(View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({'results': []})

        users = GitHubUser.objects.filter(
            Q(github_username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )[:10]  # Limit to 10 results

        results = [{
            'github_username': user.github_username,
            'name': user.full_name,
            'avatar_url': user.avatar_url or '',
            'url': user.get_absolute_url(),
            'country': user.country.name if user.country else ''
        } for user in users]

        return JsonResponse({'results': results})