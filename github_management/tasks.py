# github_management/tasks.py
import logging
from celery import shared_task
from django.utils import timezone
from django.core.management import call_command
from django.db import transaction
from .models import Country, GitHubUser
from .services.github_api import GitHubAPIClient

logger = logging.getLogger(__name__)

# github_management/tasks.py

@shared_task(bind=True)
def fetch_all_countries_users(self):
    """Background task to fetch users for all countries"""
    countries = Country.objects.all()
    for country in countries:
        fetch_users_for_country.delay(country.id)
    return f"Started fetching users for {countries.count()} countries"

@shared_task(bind=True)
def fetch_users_for_country(self, country_id):
    """Background task to fetch users for a specific country"""
    try:
        country = Country.objects.get(id=country_id)
        client = GitHubAPIClient()
        users = client.get_users_by_country(country.slug)
        
        # Rest of your existing code remains the same...
        user_objs = []
        for user_data in users:
            user_objs.append(GitHubUser(
                github_username=user_data['username'],
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                followers=user_data.get('followers', 0),
                contributions_last_year=user_data.get('contributions', 0),
                country=country,
                rank=user_data.get('rank', 0),
                profile_url=user_data.get('profile_url', f"https://github.com/{user_data['username']}"),
                avatar_url=user_data.get('avatar_url', f"https://github.com/{user_data['username']}.png")
            ))
        
        existing = GitHubUser.objects.filter(github_username__in=[obj.github_username for obj in user_objs])
        existing_usernames = {user.github_username for user in existing}

        to_create = [obj for obj in user_objs if obj.github_username not in existing_usernames]
        GitHubUser.objects.bulk_create(to_create)
        
        # Update country stats
        country.user_count = len(user_objs)
        country.last_updated = timezone.now()
        country.save()
        
        logger.info(f"Successfully fetched {len(user_objs)} users for {country.name}")
        
    except Exception as e:
        logger.error(f"Error fetching users for country {country_id}: {e}", exc_info=True)
        raise
    finally:
        # Make sure to mark as not fetching even if there was an error
        Country.objects.filter(id=country_id).update(is_fetching=False)

@shared_task
def update_users_stats_batch(user_ids, model_name):
    """
    Update multiple users' stats in a single task using their primary keys.
    """
    from .models import GitHubUser
    from users.models import User
    from .services.github_api import GitHubAPI
    from django.utils import timezone

    github_api = GitHubAPI()

    # Map model name string to actual model class
    model_map = {
        "GitHubUser": GitHubUser,
        "User": User,
    }

    model_class = model_map.get(model_name)
    if not model_class:
        raise ValueError(f"Invalid model name: {model_name}")

    # Get all users at once to minimize database queries
    users = model_class.objects.in_bulk(user_ids)

    for user_id, user in users.items():
        try:
            user_data = github_api.get_user(user.github_username)
            
            if user_data:
                update_fields = ['fetched_at']
                user.fetched_at = timezone.now()
                
                if user_data.get('followers') is not None and user.followers != user_data['followers']:
                    user.followers = user_data['followers']
                    update_fields.append('followers')
                    
                if user_data.get('following') is not None and user.following != user_data['following']:
                    user.following = user_data['following']
                    update_fields.append('following')
                    
                contributions = user_data.get('contributions', {})
                contributions_last_year = contributions.get('last_year', 0)
                print(f"Contributions last year: {contributions_last_year}")
                # if user.contributions_last_year != contributions_last_year:
                #     user.contributions_last_year = contributions_last_year
                #     update_fields.append('contributions_last_year')
                    
                if user_data.get('avatar_url') and user.avatar_url != user_data['avatar_url']:
                    user.avatar_url = user_data['avatar_url']
                    update_fields.append('avatar_url')
                    
                if user_data.get('html_url') and user.profile_url != user_data['html_url']:
                    user.profile_url = user_data['html_url']
                    update_fields.append('profile_url')
                
                if len(update_fields) > 1:  # More than just fetched_at
                    user.save(update_fields=update_fields)
                
        except Exception as e:
            logger.error(f"Error updating user {user.github_username}: {e}")
            continue  # Continue with next user even if one fails