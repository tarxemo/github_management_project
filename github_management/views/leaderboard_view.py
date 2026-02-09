from django.shortcuts import render, get_object_or_404
from django.views import View
from ..models import Leaderboard, Country
from django.db.models import Q

class LeaderboardView(View):
    """View to display various leaderboards."""
    
    def get(self, request):
        lb_type = request.GET.get('type', Leaderboard.LeaderboardType.INTELLIGENCE)
        country_slug = request.GET.get('country')
        language = request.GET.get('language')
        
        # Get the specific leaderboard
        leaderboard = Leaderboard.objects.filter(
            leaderboard_type=lb_type,
            country_slug=country_slug,
            language=language
        ).first()
        
        # Get countries for filtering
        countries = Country.objects.all().order_by('name')
        
        # Get available languages
        languages = Leaderboard.objects.values_list('language', flat=True).distinct().exclude(language__isnull=True)
        
        context = {
            'leaderboard': leaderboard,
            'lb_type': lb_type,
            'current_country': country_slug,
            'current_language': language,
            'countries': countries,
            'languages': languages,
            'lb_types': Leaderboard.LeaderboardType.choices,
            'active_tab': 'leaderboard'
        }
        
        return render(request, 'github_management/leaderboard.html', context)
