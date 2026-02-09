from django.utils import timezone
from github_management.models import GitHubUser, Country
from github_management.services.github_api import GitHubAPI
import logging

logger = logging.getLogger(__name__)

class UserSyncService:
    """Service to handle on-the-fly synchronization of GitHub users."""

    @classmethod
    def get_or_create_user(cls, username):
        """
        Retrieves a user from the database or fetches it from GitHub if missing.
        Returns Tuple[GitHubUser, bool]: (user_object, was_created)
        """
        # 1. Try local lookup (case-insensitive)
        user = GitHubUser.objects.filter(github_username__iexact=username).first()
        if user:
            return user, False
            
        # 2. Fetch from GitHub synchronously for basic stats
        logger.info(f"User {username} not found locally. Fetching from GitHub API...")
        api = GitHubAPI()
        user_data = api.get_user(username)
        if not user_data or 'login' not in user_data:
            logger.warning(f"Could not fetch data for GitHub user: {username}")
            return None, False
            
        # 3. Handle Country mapping
        location = user_data.get('location')
        country = None
        if location:
            # Attempt to find a country that matches the user's location string
            # This is a simple heuristic matching
            country = Country.objects.filter(name__icontains=location).first()
            if not country:
                # Try to extract the last part of the location (often the country)
                parts = [p.strip() for p in location.split(',')]
                if len(parts) > 1:
                    country = Country.objects.filter(name__icontains=parts[-1]).first()
            
        if not country:
            # Fallback to a 'Global' country entry
            country, _ = Country.objects.get_or_create(
                slug='global',
                defaults={'name': 'Global', 'user_count': 0}
            )
            
        # 4. Create local GitHubUser
        # We populate basic fields immediately so badges have data to show
        stats = user_data.get('stats', {})
        contributions = stats.get('contributions', {})
        
        user = GitHubUser.objects.create(
            github_username=user_data.get('login', username),
            display_name=user_data.get('name'),
            avatar_url=user_data.get('avatar_url'),
            profile_url=user_data.get('html_url'),
            followers=user_data.get('followers', 0),
            following=user_data.get('following', 0),
            public_repos=user_data.get('public_repos', 0),
            public_gists=user_data.get('public_gists', 0),
            contributions_last_year=contributions.get('last_year', 0),
            country=country,
            github_created_at=user_data.get('created_at'),
            fetched_at=timezone.now()
        )

        # 5. Synchronously create repository records for stars (top 10)
        from github_management.models import GitHubRepository, DeveloperSkill
        top_repos = stats.get('top_repos', [])
        repo_objs = []
        for i, r in enumerate(top_repos):
            repo_objs.append(GitHubRepository(
                owner_username=user.github_username,
                name=r['name'],
                full_name=f"{user.github_username}/{r['name']}",
                stargazers_count=r['stars'],
                github_id=r.get('github_id'),
                node_id=r.get('node_id'),
                html_url=f"{user.profile_url}/{r['name']}",
                github_created_at=timezone.now(),
                github_updated_at=timezone.now()
            ))
        if repo_objs:
            GitHubRepository.objects.bulk_create(repo_objs, ignore_conflicts=True)

        # 6. Synchronously create language/skill records
        languages = stats.get('languages', {})
        skill_objs = []
        for lang_name, count in languages.items():
            skill = DeveloperSkill(
                github_username=user.github_username,
                skill_name=lang_name,
                skill_category=DeveloperSkill.SkillCategory.LANGUAGE,
                repo_count=count,
                last_used=timezone.now()
            )
            # Pre-compute proficiency to satisfy ranking
            skill.compute_proficiency()
            skill_objs.append(skill)
        if skill_objs:
            DeveloperSkill.objects.bulk_create(skill_objs)
        
        # 7. Trigger full deep sync (repos, events, skills) in background to replace placeholders
        from github_management.tasks import sync_all_user_data_task
        sync_all_user_data_task.delay(user.github_username)
        
        logger.info(f"Successfully created on-the-fly record for {user.github_username}")
        return user, True
