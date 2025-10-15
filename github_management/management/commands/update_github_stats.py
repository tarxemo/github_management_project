# github_management/management/commands/update_github_stats.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from github_management.models import GitHubUser
from github_management.services.github_api import GitHubAPI
from datetime import timedelta
from django.db.models import Q

class Command(BaseCommand):
    help = 'Update GitHub user statistics (followers, following, contributions)'

    def handle(self, *args, **options):
        # Only update users fetched more than 1 hour ago
        threshold = timezone.now() - timedelta(hours=1)
        users_to_update = GitHubUser.objects.filter(
            Q(fetched_at__isnull=True) | 
            Q(fetched_at__lt=threshold)
        )[:100]  # Limit to 100 users per run to avoid rate limiting

        updated = 0
        for user in users_to_update:
            try:
                self.update_user_stats(user)
                updated += 1
            except Exception as e:
                self.stderr.write(f"Error updating {user.github_username}: {str(e)}")

        self.stdout.write(f"Successfully updated {updated} users")

    def update_user_stats(self, user):
        github_api = GitHubAPI()
        user_data = github_api.get_user(user.github_username)
        
        if user_data:
            user.followers = user_data.get('followers', 0)
            print(user.followers)
            user.following = user_data.get('following', 0)
            user.contributions_last_year = user_data.get('contributions', {}).get('last_year', 0)
            user.avatar_url = user_data.get('avatar_url', user.avatar_url)
            user.profile_url = user_data.get('html_url', user.profile_url)
            user.fetched_at = timezone.now()
            user.save()