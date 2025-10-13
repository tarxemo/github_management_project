# tasks.py
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from .models import Country, GitHubUser
from .services.github_api import GitHubAPIClient
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def fetch_users_for_country(self, country_id):
    """Background task to fetch users for a specific country"""
    # country = Country.objects.get(id=country_id)
    
    try:
        client = GitHubAPIClient()
        for country in Country.objects.all():
            if GitHubUser.objects.filter(country=country).exists():
                continue
            users = client.get_users_by_country(country.slug)
            # with transaction.atomic():
                # Delete existing users for this country
            country.users.all().delete()
            
            # Create new users
            user_objs = []
            for user_data in users:
                user_objs.append(GitHubUser(
                    username=user_data['username'],
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    followers=user_data.get('followers', 0),
                    contributions_last_year=user_data.get('contributions', 0),
                    country=country,
                    rank=user_data.get('rank', 0),
                    profile_url=user_data.get('profile_url', f"https://github.com/{user_data['username']}"),
                    avatar_url=user_data.get('avatar_url', f"https://github.com/{user_data['username']}.png")
                ))
            
            existing = GitHubUser.objects.filter(username__in=[obj.username for obj in user_objs])
            existing_usernames = {user.username for user in existing}

            to_create = [obj for obj in user_objs if obj.username not in existing_usernames]
            GitHubUser.objects.bulk_create(to_create)
            
            # Update country stats
            country.user_count = len(user_objs)
            country.last_updated = timezone.now()
            country.save()
            
            logger.info(f"Successfully fetched {len(user_objs)} users for {country.name}")
            
    except Exception as e:
        logger.error(f"Error fetching users for {country.name}: {e}", exc_info=True)
        raise
    finally:
        # Make sure to mark as not fetching even if there was an error
        Country.objects.filter(id=country.id).update(is_fetching=False)