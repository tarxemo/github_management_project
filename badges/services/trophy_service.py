from typing import List, Dict, Any
from github_management.models import GitHubUser, GitHubRepository, DeveloperSkill
from django.utils import timezone
from django.db.models import Sum
import math

class TrophyService:
    """Service to calculate GitHub Trophies based on user statistics."""

    RANKS = ['SSS', 'SS', 'S', 'AAA', 'AA', 'A', 'B', 'C', 'UNKNOWN']

    @classmethod
    def get_trophies(cls, user: GitHubUser) -> List[Dict[str, Any]]:
        """Calculate all trophies for a user."""
        trophies = []
        
        # 1. Stars Trophy
        total_stars = GitHubRepository.objects.filter(owner_username=user.github_username).aggregate(Sum('stargazers_count'))['stargazers_count__sum'] or 0
        trophies.append(cls._create_trophy("Stars", total_stars, cls._get_stars_rank(total_stars)))

        # 2. Followers Trophy
        followers = user.followers or 0
        trophies.append(cls._create_trophy("Followers", followers, cls._get_followers_rank(followers)))

        # 3. Contributions Trophy (last year)
        contributions = user.contributions_last_year or 0
        trophies.append(cls._create_trophy("Commits", contributions, cls._get_commits_rank(contributions)))

        # 4. Repositories Trophy
        repos = user.public_repos or 0
        trophies.append(cls._create_trophy("Repositories", repos, cls._get_repos_rank(repos)))

        # 5. Multi-Language Trophy
        langs_count = DeveloperSkill.objects.filter(github_username=user.github_username, skill_category=DeveloperSkill.SkillCategory.LANGUAGE).count()
        trophies.append(cls._create_trophy("Languages", langs_count, cls._get_langs_rank(langs_count)))

        # 6. Account Age Trophy
        if user.github_created_at:
            delta = timezone.now() - user.github_created_at
            years = round(delta.days / 365.25, 1)
            trophies.append(cls._create_trophy("Account Age", years, cls._get_age_rank(years)))

        # Sort trophies by rank (highest first)
        trophies.sort(key=lambda t: cls.RANKS.index(t['rank']))

        return trophies

    @classmethod
    def _create_trophy(cls, title: str, value: Any, rank: str) -> Dict[str, Any]:
        rank_data = cls._get_rank_data(rank)
        # Format the display value
        display_value = str(value)
        if title == "Account Age":
            display_value = f"{value}y"
            
        return {
            "title": title,
            "value": display_value,
            "rank": rank,
            **rank_data
        }

    @classmethod
    def _get_rank_data(cls, rank: str) -> Dict[str, Any]:
        """Get visual metadata for a rank."""
        # Professional color palettes (Gold, Silver, Bronze, etc.)
        config = {
            'SSS': {
                'color': '#ff79c6', 'grad_1': '#ff79c6', 'grad_2': '#bd93f9', 
                'show_leaves': True, 'label': 'God Tier'
            },
            'SS': {
                'color': '#ffb86c', 'grad_1': '#ffb86c', 'grad_2': '#ff79c6',
                'show_leaves': True, 'label': 'Legendary'
            },
            'S': {
                'color': '#f1fa8c', 'grad_1': '#f1fa8c', 'grad_2': '#ffb86c',
                'show_leaves': True, 'label': 'Master'
            },
            'AAA': {
                'color': '#8be9fd', 'grad_1': '#8be9fd', 'grad_2': '#50fa7b',
                'show_leaves': True, 'label': 'Elite'
            },
            'AA': {
                'color': '#50fa7b', 'grad_1': '#50fa7b', 'grad_2': '#8be9fd',
                'show_leaves': False, 'label': 'Pro'
            },
            'A': {
                'color': '#bd93f9', 'grad_1': '#bd93f9', 'grad_2': '#ff79c6',
                'show_leaves': False, 'label': 'Expert'
            },
            'B': {
                'color': '#ff5555', 'grad_1': '#ff5555', 'grad_2': '#ffb86c',
                'show_leaves': False, 'label': 'Rising'
            },
            'C': {
                'color': '#6272a4', 'grad_1': '#6272a4', 'grad_2': '#44475a',
                'show_leaves': False, 'label': 'Starter'
            },
        }
        return config.get(rank, {
            'color': '#44475a', 'grad_1': '#6272a4', 'grad_2': '#282a36',
            'show_leaves': False, 'label': 'Learner'
        })

    @classmethod
    def _calculate_rank(cls, value: float, thresholds: List[float]) -> str:
        for i, threshold in enumerate(thresholds):
            if value >= threshold:
                return cls.RANKS[i]
        return cls.RANKS[-1]

    @classmethod
    def _get_stars_rank(cls, stars: int) -> str:
        return cls._calculate_rank(stars, [5000, 2000, 1000, 500, 250, 100, 50, 10])

    @classmethod
    def _get_followers_rank(cls, followers: int) -> str:
        return cls._calculate_rank(followers, [1000, 500, 250, 100, 50, 25, 10, 5])

    @classmethod
    def _get_commits_rank(cls, commits: int) -> str:
        return cls._calculate_rank(commits, [10000, 5000, 2500, 1000, 500, 250, 100, 50])

    @classmethod
    def _get_repos_rank(cls, repos: int) -> str:
        return cls._calculate_rank(repos, [100, 75, 50, 40, 30, 20, 10, 5])

    @classmethod
    def _get_langs_rank(cls, count: int) -> str:
        return cls._calculate_rank(count, [20, 15, 10, 8, 6, 4, 3, 2])

    @classmethod
    def _get_age_rank(cls, years: float) -> str:
        return cls._calculate_rank(years, [15, 12, 10, 7, 5, 3, 1, 0.5])
