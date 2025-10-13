# users/tasks.py
from __future__ import absolute_import

from github import Github
from celery import shared_task
from django.conf import settings
from django.apps import apps

def get_user_model():
    return apps.get_model('users', 'User')

def get_userfollowing_model():
    return apps.get_model('users', 'UserFollowing')

@shared_task(bind=True, name="users.tasks.sync_github_followers_following")
def sync_github_followers_following(self, user_id):
    """
    Sync GitHub followers and following for a user.
    This task is called automatically when a new user is created with a GitHub access token.
    """
    try:
        User = get_user_model()
        user = User.objects.get(id=user_id)
        if not user.github_access_token:
            print(f"No GitHub access token for user {user_id}")
            return

        print(f"Starting GitHub sync for user {user.email}")

        g = Github(user.github_access_token)
        github_user = g.get_user()

        # Get current followers and following from GitHub
        github_followers = {follower.login.lower(): follower for follower in github_user.get_followers()}
        github_following = {following.login.lower(): following for following in github_user.get_following()}

        print(f"Found {len(github_followers)} followers and {len(github_following)} following on GitHub")

        # Process all GitHub users we have relationships with
        all_github_users = set(github_followers.keys()) | set(github_following.keys())

        # Get or create user objects for all GitHub users
        User = get_user_model()
        users_to_create = []
        existing_users = {u.github_username.lower(): u for u in User.objects.filter(
            github_username__in=all_github_users
        ) if u.github_username}  # Only include users with github_username
        for username in all_github_users:
            if username not in existing_users:
                gh_user = github_followers.get(username) or github_following[username]
                # Create user with only the fields that exist in your User model
                email = getattr(gh_user, 'email', '')
                if not email and hasattr(gh_user, 'login'):
                    email = f"{gh_user.login}@users.noreply.github.com"
                
                user_data = {
                    'email': email,
                    'github_username': username,
                    'github_avatar_url': getattr(gh_user, 'avatar_url', ''),
                    'github_profile_url': getattr(gh_user, 'html_url', ''),
                    'is_active': False,  # External users are not active by default
                    'is_internal': False,  # This is an external GitHub user
                    'password': '!',  # Required field, but we'll set an unusable password
                    'is_staff': False,
                    'is_superuser': False
                }
                User = get_user_model()
                users_to_create.append(User(**user_data))
        
        if users_to_create:
            try:
                User.objects.bulk_create(users_to_create, ignore_conflicts=True)
            except Exception as e:
                print(f"Error creating users: {e}")
                # Try creating users one by one to identify the problematic one
                for user in users_to_create:
                    try:
                        user.save()
                    except Exception as e:
                        print(f"Failed to create user {user.github_username}: {e}")
            
            # Refresh existing users
            User = get_user_model()
            existing_users = {u.github_username.lower(): u for u in User.objects.filter(
                github_username__in=all_github_users
            ) if u.github_username}

        # Update relationships
        UserFollowing = get_userfollowing_model()
        for username, gh_user in {**github_followers, **github_following}.items():
            target_user = existing_users.get(username.lower())
            if not target_user:
                continue
                
            is_follower = username in github_followers
            is_following = username in github_following

            if is_follower and is_following:
                # This is a mutual relationship
                UserFollowing.follow(target_user, user)  # They follow us
                UserFollowing.follow(user, target_user)   # We follow them
            elif is_follower:
                # They follow us
                UserFollowing.follow(target_user, user)
            elif is_following:
                # We follow them
                UserFollowing.follow(user, target_user)

        # Clean up any relationships that no longer exist on GitHub
        UserFollowing = get_userfollowing_model()
        
        # Get the actual User objects, not the relationship objects
        current_following = set(rel.to_user.github_username.lower() 
                              for rel in UserFollowing.get_following(user) 
                              if rel.to_user.github_username)
        current_followers = set(rel.from_user.github_username.lower() 
                              for rel in UserFollowing.get_followers(user) 
                              if rel.from_user.github_username)
        
        # Remove relationships that no longer exist
        for username in (current_following - set(github_following.keys())):
            try:
                User = get_user_model()
                UserFollowing = get_userfollowing_model()
                target_user = User.objects.get(github_username__iexact=username)
                # Use the unfollow method on the model
                UserFollowing.objects.filter(from_user=user, to_user=target_user).delete()
            except (User.DoesNotExist, UserFollowing.DoesNotExist):
                pass

    except Exception as e:
        print(f"Error in sync_github_followers_following: {e}")
        raise