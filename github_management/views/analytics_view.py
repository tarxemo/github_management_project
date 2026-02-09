from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models import GitHubUser, GrowthAnalytics
from ..services.growth_analytics_service import GrowthAnalyticsService

class AnalyticsDashboardView(LoginRequiredMixin, View):
    """View for developer personal growth analytics."""
    
    def get(self, request):
        username = request.user.github_username
        if not username:
             return render(request, 'github_management/analytics_dashboard.html', {
                'error': 'No GitHub profile linked to your account.'
            })
            
        # Get growth trends
        days = int(request.GET.get('days', 30))
        trends = GrowthAnalyticsService.get_growth_trends(username, days=days)
        
        # Get latest snapshot
        latest = trends.last() if trends.exists() else None
        
        context = {
            'trends': trends,
            'latest': latest,
            'days': days,
            'active_tab': 'analytics'
        }
        
        return render(request, 'github_management/analytics_dashboard.html', context)
