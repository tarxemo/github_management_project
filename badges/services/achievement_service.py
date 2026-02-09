import logging
from django.utils import timezone
from github_management.models import GitHubUser, GitHubRepository, GitHubEvent, DeveloperSkill
from badges.models import Achievement, UserAchievement

logger = logging.getLogger(__name__)

class AchievementService:
    """Service to handle achievement calculations and unlocking."""
    
    @classmethod
    def check_user_milestones(cls, user):
        """Check all possible achievements for a user."""
        if not user or not user.is_authenticated:
            return []
            
        unlocked = []
        achievements = Achievement.objects.filter(is_active=True)
        
        for ach in achievements:
            if cls.evaluate_condition(user, ach):
                ua, created = UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=ach,
                    defaults={'is_unlocked': True, 'earned_at': timezone.now()}
                )
                if created or not ua.is_unlocked:
                    ua.is_unlocked = True
                    ua.earned_at = timezone.now()
                    ua.save()
                    unlocked.append(ach)
                    
        return unlocked

    @classmethod
    def evaluate_condition(cls, user, achievement):
        """Evaluate if a user meets an achievement condition."""
        # Simple condition evaluation based on GitHubUser data since User inherits from BaseUser
        # We can also check related models like repos or events
        
        username = getattr(user, 'github_username', None)
        if not username:
            return False
            
        val = achievement.condition_value
        ctype = achievement.condition_type
        
        if ctype == 'followers_count':
            return user.followers >= val
        elif ctype == 'contributions_count':
            return user.contributions_last_year >= val
        elif ctype == 'repositories_count':
            return GitHubRepository.objects.filter(owner_username=username).count() >= val
        elif ctype == 'stars_received':
            stars = GitHubRepository.objects.filter(owner_username=username).aggregate(models.Sum('stargazers_count'))['stargazers_count__sum'] or 0
            return stars >= val
        elif ctype == 'languages_count':
            return DeveloperSkill.objects.filter(github_username=username, skill_category=DeveloperSkill.SkillCategory.LANGUAGE).count() >= val
            
        return False

    @classmethod
    def seed_default_achievements(cls):
        """Seed common achievements into the database."""
        defaults = [
            {
                'name': 'Novice Coder',
                'slug': 'novice-coder',
                'description': 'Reach 10 contributions in the last year.',
                'icon_name': 'code',
                'points': 10,
                'tier': Achievement.Tier.BRONZE,
                'condition_type': 'contributions_count',
                'condition_value': 10
            },
            {
                'name': 'Social Butterfly',
                'slug': 'social-butterfly',
                'description': 'Reach 50 followers on GitHub.',
                'icon_name': 'users',
                'points': 20,
                'tier': Achievement.Tier.SILVER,
                'condition_type': 'followers_count',
                'condition_value': 50
            },
            {
                'name': 'Polyglot',
                'slug': 'polyglot',
                'description': 'Use 5 different programming languages.',
                'icon_name': 'languages',
                'points': 50,
                'tier': Achievement.Tier.GOLD,
                'condition_type': 'languages_count',
                'condition_value': 5
            },
            {
                'name': 'Star Collector',
                'slug': 'star-collector',
                'description': 'Receive 100 total stars across your repositories.',
                'icon_name': 'star',
                'points': 100,
                'tier': Achievement.Tier.GOLD,
                'condition_type': 'stars_received',
                'condition_value': 100
            }
        ]
        
        for data in defaults:
            Achievement.objects.get_or_create(slug=data['slug'], defaults=data)
