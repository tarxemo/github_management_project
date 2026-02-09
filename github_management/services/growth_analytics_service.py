import logging
from django.utils import timezone
from datetime import timedelta
from github_management.models import GitHubUser, GrowthAnalytics, GitHubRepository
from django.db.models import Sum

logger = logging.getLogger(__name__)

class GrowthAnalyticsService:
    """Service to capture and analyze developer growth trends."""
    
    @classmethod
    def capture_daily_snapshot(cls, username):
        """Take a snapshot of current user metrics and calculate deltas."""
        try:
            user = GitHubUser.objects.filter(github_username=username).first()
            if not user:
                return None
                
            today = timezone.now().date()
            yesterday = today - timedelta(days=1)
            
            # Get latest stats
            stars = GitHubRepository.objects.filter(owner_username=username).aggregate(Sum('stargazers_count'))['stargazers_count__sum'] or 0
            
            # Get previous snapshot
            prev = GrowthAnalytics.objects.filter(github_username=username, date__lt=today).order_by('-date').first()
            
            snapshot, created = GrowthAnalytics.objects.update_or_create(
                github_username=username,
                date=today,
                defaults={
                    'followers_count': user.followers,
                    'following_count': user.following,
                    'public_repos_count': user.public_repos,
                    'contributions_count': user.contributions_last_year,
                    'stars_received_count': stars,
                }
            )
            
            if prev:
                snapshot.followers_delta = snapshot.followers_count - prev.followers_count
                snapshot.stars_delta = snapshot.stars_received_count - prev.stars_received_count
                snapshot.contributions_delta = snapshot.contributions_count - prev.contributions_count
                
                if snapshot.followers_count > 0:
                    snapshot.engagement_rate = (snapshot.stars_received_count / snapshot.followers_count) * 10
                    
                snapshot.save()
                
            return snapshot
        except Exception as e:
            logger.error(f"Error capturing growth snapshot for {username}: {e}")
            return None

    @classmethod
    def get_growth_trends(cls, username, days=30):
        """Return growth metrics for the last N days for visualization."""
        start_date = timezone.now().date() - timedelta(days=days)
        return GrowthAnalytics.objects.filter(
            github_username=username, 
            date__gte=start_date
        ).order_by('date')
