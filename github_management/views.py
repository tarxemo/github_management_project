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

logger = logging.getLogger(__name__)

class CountryListView(View):
    """View to list all available countries"""
    def get(self, request):
        countries = Country.objects.all().order_by('name')
        return render(request, 'github_management/country_list.html', {
            'countries': countries,
            'active_tab': 'countries'
        })

class CountryDetailView(View):
    """View to show users for a specific country"""
    def get(self, request, slug):
        country = get_object_or_404(Country, slug=slug)
        users = country.users.all().order_by('rank')
        
        # Pagination
        paginator = Paginator(users, 25)  # Show 25 users per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
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

class FollowRandomUsersView(LoginRequiredMixin, View):
    """View to follow random users from any country"""
    def get(self, request):
        # Get users not already followed by the current user, ordered randomly
        users_to_follow = GitHubUser.objects.exclude(
            follow_actions__user=request.user
        ).select_related('country').order_by('?')[:50]  # Show first 50 random users
        
        # Get all countries for the filter dropdown
        countries = Country.objects.all().order_by('name')
        
        # Get the most common country from the users to follow (for display purposes)
        country = users_to_follow[0].country.name if users_to_follow else None
        
        return render(request, 'github_management/follow_random.html', {
            'country': country,
            'countries': countries,
            'users': users_to_follow,
            'active_tab': 'follow'
        })
    
    def post(self, request):
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
                GitHubFollowAction.follow_github_user(request.user, user.id)
                followed += 1
            except Exception as e:
                logger.error(f"Error following user {user.username}: {e}")
        
        messages.success(
            request, 
            f"Started following {followed} new users from {country_name}."
        )
        return redirect('github_management:follow_random')
    
    
class FollowUserView(LoginRequiredMixin, View):
    """API endpoint to follow a specific GitHub user"""
    def post(self, request, user_id):
        github_user = get_object_or_404(GitHubUser, id=user_id)
        
        try:
            follow_action = GitHubFollowAction.follow_github_user(request.user, github_user)
            return JsonResponse({
                'success': True,
                'message': f'Started following {github_user.username}',
                'action_id': follow_action.id
            })
        except Exception as e:
            logger.error(f"Error following user {github_user.username}: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Failed to follow user: {str(e)}'
            }, status=400)


class UnfollowNonFollowersView(LoginRequiredMixin, View):
    """View to unfollow users who haven't followed back"""
    def get(self, request):
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


class UpdateFollowStatusView(LoginRequiredMixin, View):
    """API endpoint to update follow status for a user"""
    def post(self, request, action_id):
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