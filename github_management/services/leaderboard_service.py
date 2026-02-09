import logging
from django.db import models
from github_management.models import GitHubUser, Country, Leaderboard, LeaderboardEntry, DeveloperSkill
from django.db.models import Sum, Count, Q

logger = logging.getLogger(__name__)

class LeaderboardService:
    """Service to manage and update leaderboards."""
    
    @classmethod
    def update_all_leaderboards(cls):
        """Trigger update for all active leaderboards."""
        # Global Intelligence Leaderboard
        cls.update_leaderboard(Leaderboard.LeaderboardType.INTELLIGENCE)
        
        # Most Followers Global
        cls.update_leaderboard(Leaderboard.LeaderboardType.FOLLOWERS)
        
        # Country-specific leaderboards
        countries = Country.objects.all()
        for country in countries:
            cls.update_leaderboard(
                Leaderboard.LeaderboardType.INTELLIGENCE, 
                country_slug=country.slug
            )
            
        return "Started updating all leaderboards"

    @classmethod
    def update_leaderboard(cls, lb_type, country_slug=None, language=None):
        """Compute and update a specific leaderboard."""
        lb, created = Leaderboard.objects.get_or_create(
            leaderboard_type=lb_type,
            country_slug=country_slug,
            language=language
        )
        
        # Define base query
        query = GitHubUser.objects.all()
        if country_slug:
            query = query.filter(country__slug=country_slug)
        
        # Define sorting and score based on type
        if lb_type == Leaderboard.LeaderboardType.INTELLIGENCE:
            query = query.order_by('-intelligence_score', '-contributions_last_year')
            score_attr = 'intelligence_score'
        elif lb_type == Leaderboard.LeaderboardType.FOLLOWERS:
            query = query.order_by('-followers', '-intelligence_score')
            score_attr = 'followers'
        elif lb_type == Leaderboard.LeaderboardType.CONTRIBUTIONS:
            query = query.order_by('-contributions_last_year', '-intelligence_score')
            score_attr = 'contributions_last_year'
        else:
            return None

        # Fetch top 100
        top_users = list(query[:100])
        
        # Update/Create entries
        old_entries_map = {e.github_username: e.rank for e in lb.entries.all()}
        
        new_entries_data = []
        for idx, gh_user in enumerate(top_users, start=1):
            score = getattr(gh_user, score_attr) or 0
            
            entry, entry_created = LeaderboardEntry.objects.update_or_create(
                leaderboard=lb,
                github_username=gh_user.github_username,
                defaults={
                    'rank': idx,
                    'score': float(score),
                    'display_data': {
                        'avatar_url': gh_user.avatar_url,
                        'name': gh_user.full_name,
                        'contributions': gh_user.contributions_last_year,
                    },
                    'previous_rank': old_entries_map.get(gh_user.github_username),
                }
            )
            if entry.previous_rank:
                entry.rank_change = entry.previous_rank - entry.rank
                entry.save(update_fields=['rank_change'])
            
            new_entries_data.append({
                'rank': idx,
                'username': gh_user.github_username,
                'score': float(score)
            })
            
        # Remove entries that are no longer in top 100
        current_usernames = [u.github_username for u in top_users]
        lb.entries.exclude(github_username__in=current_usernames).delete()
        
        # Update leaderboard snapshot
        lb.rankings = new_entries_data
        lb.total_entries = len(new_entries_data)
        lb.is_stale = False
        lb.save()
        
        return lb
