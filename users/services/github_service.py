# users/services/github_service.py
from github import Github, GithubException
from django.conf import settings
import requests
from django.db import transaction
from users.models import User, UserFollowing

class GitHubService:
    @staticmethod
    def get_github_client(access_token):
        """Get authenticated GitHub client"""
        return Github(access_token, timeout=10, per_page=100)

    @classmethod
    @transaction.atomic
    def follow_user_on_github(cls, user, target_username):
        """Follow a user on GitHub and update local database"""
        access_token = user.github_access_token
        if not access_token:
            print("❌ No GitHub access token found for user")
            return False

        try:
            g = cls.get_github_client(access_token)
            github_user = g.get_user()

            # Validate target username
            try:
                target_user = g.get_user(target_username)
                target_username = target_user.login
            except GithubException as e:
                print(f"❌ Target user {target_username} not found: {e}")
                return False

            # Check if already following
            if github_user.has_in_following(target_user):
                print(f"✅ Already following {target_username}")
                return True

            # Use direct REST API
            url = f"https://api.github.com/user/following/{target_username}"
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github+json",
                "Content-Length": "0"
            }

            response = requests.put(url, headers=headers)
            if response.status_code == 204:
                print(f"✅ Successfully followed {target_username}")
                # Update local database
                target_user_obj, created = User.objects.get_or_create(
                    github_username__iexact=target_username,
                    defaults={
                        'github_username': target_username,
                        'is_active': False,
                        'is_internal': False
                    }
                )
                if created:
                    target_user_obj.avatar_url = target_user.avatar_url
                    target_user_obj.first_name = target_user.name
                    target_user_obj.last_name = target_user.name
                    target_user_obj.is_active = True
                    target_user_obj.is_internal = True
                    target_user_obj.save()
                # Create or update the following relationship
                UserFollowing.objects.update_or_create(
                    from_user=user,
                    to_user=target_user_obj
                )
                
                return True
            
            elif response.status_code == 404:
                print("❌ 404: Token likely missing 'user:follow' permission or user not found")
            else:
                print(f"❌ Error: {response.status_code} -> {response.text}")
            return False

        except GithubException as e:
            print(f"GitHub API error following {target_username}: {e.data.get('message', str(e))}")
            return False
        except Exception as e:
            print(f"Unexpected error following {target_username}: {str(e)}")
            return False

    @classmethod
    @transaction.atomic
    def unfollow_user_on_github(cls, user, target_username):
        """Unfollow a user on GitHub and update local database"""
        access_token = user.github_access_token
        if not access_token:
            print("❌ No GitHub access token found for user")
            return False

        try:
            g = cls.get_github_client(access_token)
            github_user = g.get_user()

            try:
                target_user = g.get_user(target_username)
                target_username = target_user.login
            except GithubException:
                print(f"⚠️ Target user {target_username} not found — considered already unfollowed")
                return True

            if not github_user.has_in_following(target_user):
                print(f"⚠️ Not following {target_username}")
                return True

            url = f"https://api.github.com/user/following/{target_username}"
            headers = {
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github+json",
            }

            response = requests.delete(url, headers=headers)
            if response.status_code == 204:
                print(f"✅ Successfully unfollowed {target_username}")
                
                # Update local database
                target_user_obj = User.objects.filter(
                    github_username__iexact=target_username
                ).first()
                
                if target_user_obj:
                    # Remove the following relationship
                    UserFollowing.objects.filter(
                        from_user=user,
                        to_user=target_user_obj
                    ).delete()
                    
                return True
            elif response.status_code == 404:
                print("❌ 404: Token likely missing 'user:follow' permission or user not found")
            else:
                print(f"❌ Error: {response.status_code} -> {response.text}")
            return False

        except GithubException as e:
            print(f"GitHub API error unfollowing {target_username}: {e.data.get('message', str(e))}")
            return False
        except Exception as e:
            print(f"Unexpected error unfollowing {target_username}: {str(e)}")
            return False