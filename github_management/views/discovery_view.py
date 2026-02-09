from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from ..services.developer_match_service import DeveloperMatchService
from ..models import GitHubUser, GitHubRepository

class DiscoveryFeedView(LoginRequiredMixin, View):
    """View to discover recommended developers and trending projects."""
    
    def get(self, request):
        username = request.user.github_username
        
        # 1. Get recommended developers
        recommendations = []
        if username:
            matches = DeveloperMatchService.find_matches(username, limit=12)
            recommendations = matches
            
        # 2. Get trending repositories
        trending_repos = GitHubRepository.objects.filter(
            is_fork=False
        ).order_by('-stargazers_count')[:10]
        
        # 3. Featured developers (high intelligence score)
        featured_devs = GitHubUser.objects.order_by('-intelligence_score')[:8]
        
        context = {
            'recommendations': recommendations,
            'trending_repos': trending_repos,
            'featured_devs': featured_devs,
            'active_tab': 'discovery'
        }
        
        return render(request, 'github_management/discovery_feed.html', context)
