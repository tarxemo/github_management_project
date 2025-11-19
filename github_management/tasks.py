 # github_management/tasks.py
import logging
import requests
from celery import shared_task
from django.utils import timezone
from django.core.management import call_command
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.contrib.auth import get_user_model
from .models import Country, GitHubUser, GitHubFollowAction
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
                middle_name=user_data.get('middle_name', ''),
                last_name=user_data.get('last_name', ''),
                followers=user_data.get('followers', 0),
                contributions_last_year=user_data.get('contributions', 0),
                country=country,
                rank=user_data.get('rank', 0),
                profile_url=user_data.get('profile_url', f"https://github.com/{user_data['username']}"),
                avatar_url=user_data.get('avatar_url', f"https://github.com/{user_data['username']}.png")
            ))
        
        existing = GitHubUser.objects.filter(
            github_username__in=[obj.github_username for obj in user_objs]
        )
        existing_map = {user.github_username: user for user in existing}

        to_create = []
        to_update = []

        for obj in user_objs:
            if obj.github_username in existing_map:
                existing_user = existing_map[obj.github_username]
                # Update existing fields
                existing_user.followers = obj.followers
                existing_user.contributions_last_year = obj.contributions_last_year
                existing_user.rank = obj.rank
                existing_user.profile_url = obj.profile_url
                existing_user.avatar_url = obj.avatar_url
                # Update name fields only if provided (non-empty)
                if obj.first_name:
                    existing_user.first_name = obj.first_name
                if obj.middle_name:
                    existing_user.middle_name = obj.middle_name
                if obj.last_name:
                    existing_user.last_name = obj.last_name
                to_update.append(existing_user)  # now includes PK
            else:
                to_create.append(obj)

        if to_create:
            GitHubUser.objects.bulk_create(to_create)

        if to_update:
            GitHubUser.objects.bulk_update(
                to_update,
                ['followers', 'contributions_last_year', 'rank', 'profile_url', 'avatar_url', 'first_name', 'middle_name', 'last_name']
            )

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


@shared_task(bind=True)
def recompute_country_intelligence_ranking(self, country_id):
    """Recompute intelligence_score and rank for all users in a country."""
    try:
        country = Country.objects.get(id=country_id)
    except Country.DoesNotExist:
        logger.warning(f"Country with id={country_id} does not exist")
        return

    users = list(GitHubUser.objects.filter(country=country))
    if not users:
        logger.info(f"No users found for country {country.name} to rank")
        return

    for user in users:
        user.intelligence_score = user.compute_intelligence_score()

    # Sort by intelligence score descending, then by contributions and followers as tie-breakers
    users.sort(
        key=lambda u: (
            -(u.intelligence_score or 0),
            -(u.contributions_last_year or 0),
            -(u.followers or 0),
        )
    )

    # Assign rank per country based on sorted order (1-based)
    for idx, user in enumerate(users, start=1):
        user.rank = idx

    GitHubUser.objects.bulk_update(users, ["intelligence_score", "rank"])
    logger.info(f"Recomputed intelligence ranking for {len(users)} users in {country.name}")


@shared_task(bind=True)
def recompute_all_countries_intelligence_ranking(self):
    """Recompute intelligence-based rankings for all countries."""
    for country in Country.objects.all().only("id"):
        recompute_country_intelligence_ranking.delay(country.id)


@shared_task(bind=True)
def follow_random_users_task(self, user_id, count, country_id=None):
    """Background task to follow random GitHub users for a given user."""
    try:
        User = get_user_model()
        user = User.objects.get(id=user_id)

        users_query = GitHubUser.objects.exclude(
            follow_actions__user=user
        )

        country_name = "all countries"
        if country_id:
            users_query = users_query.filter(country_id=country_id)
            try:
                country = Country.objects.get(id=country_id)
                country_name = country.name
            except Country.DoesNotExist:
                pass

        users_to_follow = list(users_query.order_by("?")[:count])

        followed = 0
        for gh_user in users_to_follow:
            try:
                GitHubFollowAction.follow_github_user(user, gh_user)
                followed += 1
            except Exception as e:
                logger.error(f"Error following user {gh_user.github_username}: {e}")

        return {"followed": followed, "country_name": country_name}
    except Exception as e:
        logger.error(f"follow_random_users_task failed for user_id={user_id}: {e}")
        raise


@shared_task(bind=True)
def unfollow_non_followers_task(self, user_id, days=3):
    """Background task to unfollow users who haven't followed back after given days."""
    try:
        User = get_user_model()
        user = User.objects.get(id=user_id)
        unfollowed_count = GitHubFollowAction.unfollow_non_followers(user, days)
        return {"unfollowed": unfollowed_count, "days": days}
    except Exception as e:
        logger.error(f"unfollow_non_followers_task failed for user_id={user_id}: {e}")
        raise


@shared_task(bind=True)
def star_user_repos_task(self, actor_user_id, target_username):
    """Star all public repositories of target_username using actor_user's GitHub token."""
    try:
        User = get_user_model()
        actor = User.objects.get(id=actor_user_id)
        token = getattr(actor, "github_access_token", None)
        if not token:
            logger.warning(f"User {actor_user_id} has no GitHub access token; skipping starring.")
            return {"starred": 0, "skipped": "no_token"}

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "GitHub-Management-App/1.0",
        }

        page = 1
        per_page = 100
        total_starred = 0

        while True:
            repos_resp = requests.get(
                f"https://api.github.com/users/{target_username}/repos",
                headers=headers,
                params={"per_page": per_page, "page": page},
                timeout=30,
            )
            if repos_resp.status_code != 200:
                logger.error(
                    "Failed to list repos for %s (status %s, body=%s)",
                    target_username,
                    repos_resp.status_code,
                    repos_resp.text,
                )
                break

            repos = repos_resp.json() or []
            if not repos:
                break

            for repo in repos:
                owner = repo.get("owner", {}).get("login")
                name = repo.get("name")
                if not owner or not name:
                    continue

                star_url = f"https://api.github.com/user/starred/{owner}/{name}"
                try:
                    star_resp = requests.put(star_url, headers=headers, timeout=30)
                    if star_resp.status_code in (204, 304):
                        total_starred += 1
                    else:
                        logger.warning(
                            "Failed to star %s/%s for user %s: %s %s",
                            owner,
                            name,
                            actor.id,
                            star_resp.status_code,
                            star_resp.text,
                        )
                except Exception as e:
                    logger.error(
                        "Error starring %s/%s for user %s: %s",
                        owner,
                        name,
                        actor.id,
                        e,
                    )

            if len(repos) < per_page:
                break
            page += 1

        return {"starred": total_starred, "target": target_username}
    except Exception as e:
        logger.error(
            "star_user_repos_task failed for actor_user_id=%s, target=%s: %s",
            actor_user_id,
            target_username,
            e,
        )
        raise

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
            print(user_data)
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
                if user.contributions_last_year != contributions_last_year:
                    user.contributions_last_year = contributions_last_year
                    update_fields.append('contributions_last_year')
                    
                if user_data.get('avatar_url') and user.avatar_url != user_data['avatar_url']:
                    user.avatar_url = user_data['avatar_url']
                    update_fields.append('avatar_url')
                    
                if user_data.get('html_url') and user.profile_url != user_data['html_url']:
                    user.profile_url = user_data['html_url']
                    update_fields.append('profile_url')
                
                # Additional profile fields from REST API
                mapping = [
                    ('github_id', 'id'),
                    ('github_node_id', 'node_id'),
                    ('display_name', 'name'),
                    ('company', 'company'),
                    ('blog', 'blog'),
                    ('location', 'location'),
                    ('email_public', 'email'),
                    ('hireable', 'hireable'),
                    ('bio', 'bio'),
                    ('twitter_username', 'twitter_username'),
                    ('public_repos', 'public_repos'),
                    ('public_gists', 'public_gists'),
                    ('account_type', 'type'),
                    ('user_view_type', 'user_view_type'),
                    ('site_admin', 'site_admin'),
                ]
                for model_field, api_field in mapping:
                    if api_field in user_data and getattr(user, model_field, None) != user_data.get(api_field):
                        setattr(user, model_field, user_data.get(api_field))
                        update_fields.append(model_field)

                # Datetime fields
                for model_field, api_field in [('github_created_at', 'created_at'), ('github_updated_at', 'updated_at')]:
                    if api_field in user_data and user_data.get(api_field):
                        dt = parse_datetime(user_data.get(api_field))
                        if dt and getattr(user, model_field) != dt:
                            setattr(user, model_field, dt)
                            update_fields.append(model_field)
                
                if len(update_fields) > 1:  # More than just fetched_at
                    user.save(update_fields=update_fields)
                
        except Exception as e:
            logger.error(f"Error updating user {user.github_username}: {e}")
            continue  # Continue with next user even if one fails