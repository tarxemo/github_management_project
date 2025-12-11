# users/services/intelligent_follow_service.py
from github import Github, GithubException
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random
import logging
from users.models import User, UserFollowing
from .github_service import GitHubService

logger = logging.getLogger(__name__)

class IntelligentFollowService:
    """Intelligent follow/unfollow service to boost user followers"""
    
    # Configuration constants
    MAX_FOLLOWS_PER_DAY = 50  # GitHub API limit is ~5000 per hour, be conservative
    MAX_UNFOLLOWS_PER_DAY = 30
    MIN_FOLLOW_BACK_TIME_HOURS = 72  # Wait 3 days before unfollowing
    TARGET_FOLLOW_RATIO = 0.3  # Target 30% follow-back rate
    
    @classmethod
    def get_potential_users_to_follow(cls, user, limit=100):
        """Get intelligent list of users to follow based on criteria"""
        if not user.github_access_token:
            return []
        
        try:
            g = Github(user.github_access_token)
            github_user = g.get_user()
            
            # Get users from repositories user starred or interacted with
            potential_users = []
            
            # Method 1: Get followers of users with similar interests
            current_following = github_user.get_following()
            for followed_user in current_following[:20]:  # Check first 20 followed users
                try:
                    their_followers = followed_user.get_followers()[:10]  # Get their followers
                    for follower in their_followers:
                        if not cls.should_skip_user(user, follower):
                            potential_users.append(follower)
                except:
                    continue
            
            # Method 2: Get users from popular repositories in user's field
            repos = github_user.get_repos(sort='updated', type='owner')[:5]
            for repo in repos:
                try:
                    stargazers = repo.get_stargazers()[:20]
                    for stargazer in stargazers:
                        if not cls.should_skip_user(user, stargazer):
                            potential_users.append(stargazer)
                except:
                    continue
            
            # Method 3: Get users from user's network (followers of followers)
            followers = github_user.get_followers()[:50]
            for follower in followers:
                try:
                    their_following = follower.get_following()[:5]
                    for following in their_following:
                        if not cls.should_skip_user(user, following):
                            potential_users.append(following)
                except:
                    continue
            
            # Remove duplicates and score users
            unique_users = list({user.login: user for user in potential_users}.values())
            scored_users = []
            
            for target_user in unique_users:
                score = cls.calculate_follow_score(user, target_user)
                if score > 0:
                    scored_users.append((score, target_user))
            
            # Sort by score and return top candidates
            scored_users.sort(key=lambda x: x[0], reverse=True)
            return [user for score, user in scored_users[:limit]]
            
        except Exception as e:
            logger.error(f"Error getting potential users to follow: {e}")
            return []
    
    @classmethod
    def should_skip_user(cls, current_user, target_user):
        """Check if we should skip following this user"""
        try:
            # Skip if already following
            if current_user.has_in_following(target_user):
                return True
            
            # Skip if user follows us (mutual follow)
            if target_user.has_in_following(current_user):
                return True
            
            # Skip if user has too many followers (less likely to follow back)
            if target_user.followers > 10000:
                return True
            
            # Skip if user follows too many people (less engaged)
            if target_user.following > 5000:
                return True
            
            # Skip if user is inactive (no recent activity)
            try:
                repos = list(target_user.get_repos(sort='updated', type='all')[:3])
                if not repos:
                    return True
                latest_repo = repos[0]
                if latest_repo.updated_at < timezone.now() - timedelta(days=180):
                    return True
            except:
                return True
            
            return False
            
        except:
            return True  # Skip on any error
    
    @classmethod
    def calculate_follow_score(cls, current_user, target_user):
        """Calculate score for how likely this user is to follow back"""
        score = 0
        
        try:
            # Base score for being active
            score += 10
            
            # Bonus for moderate follower count (more likely to follow back)
            if 100 <= target_user.followers <= 1000:
                score += 20
            elif 50 <= target_user.followers < 100:
                score += 15
            elif target_user.followers < 50:
                score += 10
            
            # Bonus for good following-to-follower ratio (indicates engagement)
            if target_user.following > 0:
                ratio = target_user.followers / target_user.following
                if 0.1 <= ratio <= 0.5:
                    score += 15
                elif 0.5 < ratio <= 1.0:
                    score += 10
            
            # Bonus for having repositories (indicates active developer)
            try:
                repos = list(target_user.get_repos(type='all'))
                if len(repos) > 0:
                    score += 5
                    # Bonus for recent activity
                    if any(repo.updated_at > timezone.now() - timedelta(days=30) for repo in repos[:5]):
                        score += 10
            except:
                pass
            
            # Bonus for having bio (indicates engaged user)
            if target_user.bio:
                score += 5
            
            # Bonus for location (indicates real user)
            if target_user.location:
                score += 3
            
            # Penalty for very popular users (less likely to follow back)
            if target_user.followers > 5000:
                score -= 20
            
            # Penalty for users who follow too many people
            if target_user.following > 2000:
                score -= 10
            
            return max(0, score)
            
        except:
            return 0
    
    @classmethod
    def intelligent_follow_users(cls, user, max_follows=None):
        """Intelligently follow users to boost followers"""
        if not user.github_access_token:
            return {"success": False, "message": "No GitHub access token"}
        
        max_follows = max_follows or cls.MAX_FOLLOWS_PER_DAY
        
        # Check daily limit
        today_follows = cls.get_today_follow_count(user)
        if today_follows >= max_follows:
            return {"success": False, "message": f"Daily follow limit reached ({max_follows})"}
        
        remaining_follows = max_follows - today_follows
        
        # Get potential users to follow
        potential_users = cls.get_potential_users_to_follow(user, remaining_follows * 2)
        
        if not potential_users:
            return {"success": False, "message": "No suitable users to follow found"}
        
        # Follow users with delay between requests
        successful_follows = 0
        failed_follows = 0
        
        for target_user in potential_users[:remaining_follows]:
            try:
                success = GitHubService.follow_user_on_github(user, target_user.login)
                if success:
                    successful_follows += 1
                    logger.info(f"Successfully followed {target_user.login}")
                else:
                    failed_follows += 1
                
                # Add delay to avoid rate limiting
                import time
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                failed_follows += 1
                logger.error(f"Error following {target_user.login}: {e}")
        
        return {
            "success": True,
            "message": f"Followed {successful_follows} users, failed: {failed_follows}",
            "successful_follows": successful_follows,
            "failed_follows": failed_follows
        }
    
    @classmethod
    def intelligent_unfollow_non_followers(cls, user, max_unfollows=None):
        """Unfollow users who haven't followed back after waiting period"""
        if not user.github_access_token:
            return {"success": False, "message": "No GitHub access token"}
        
        max_unfollows = max_unfollows or cls.MAX_UNFOLLOWS_PER_DAY
        
        # Get users we follow who don't follow us back
        try:
            g = Github(user.github_access_token)
            github_user = g.get_user()
            
            following = list(github_user.get_following())
            followers = set(follower.login for follower in github_user.get_followers())
            
            # Find users we follow who don't follow us back
            non_followers = []
            for followed_user in following:
                if followed_user.login not in followers:
                    # Check if enough time has passed
                    follow_date = cls.get_follow_date(user, followed_user.login)
                    if follow_date and (timezone.now() - follow_date) >= timedelta(hours=cls.MIN_FOLLOW_BACK_TIME_HOURS):
                        non_followers.append(followed_user)
            
            if not non_followers:
                return {"success": False, "message": "No users to unfollow (waiting period or mutual follows)"}
            
            # Unfollow users (prioritize by least likely to follow back)
            successful_unfollows = 0
            failed_unfollows = 0
            
            # Sort by score (unfollow least valuable first)
            scored_users = [(cls.calculate_keep_score(user, u), u) for u in non_followers]
            scored_users.sort(key=lambda x: x[0])
            
            for score, target_user in scored_users[:max_unfollows]:
                try:
                    success = GitHubService.unfollow_user_on_github(user, target_user.login)
                    if success:
                        successful_unfollows += 1
                        logger.info(f"Successfully unfollowed {target_user.login}")
                    else:
                        failed_unfollows += 1
                    
                    # Add delay to avoid rate limiting
                    import time
                    time.sleep(random.uniform(1, 3))
                    
                except Exception as e:
                    failed_unfollows += 1
                    logger.error(f"Error unfollowing {target_user.login}: {e}")
            
            return {
                "success": True,
                "message": f"Unfollowed {successful_unfollows} users, failed: {failed_unfollows}",
                "successful_unfollows": successful_unfollows,
                "failed_unfollows": failed_unfollows
            }
            
        except Exception as e:
            logger.error(f"Error in intelligent unfollow: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}
    
    @classmethod
    def calculate_keep_score(cls, user, target_user):
        """Calculate score for how valuable it is to keep following this user"""
        score = 0
        
        try:
            # Higher score = more valuable to keep following
            score += target_user.followers / 100  # Popular users are more valuable
            score += target_user.following / 50   # Active users are more valuable
            
            # Recent activity bonus
            try:
                repos = list(target_user.get_repos(sort='updated', type='all')[:3])
                if repos and repos[0].updated_at > timezone.now() - timedelta(days=30):
                    score += 20
            except:
                pass
            
            return score
            
        except:
            return 0
    
    @classmethod
    def get_today_follow_count(cls, user):
        """Get number of follows performed today"""
        from users.models import GitHubFollowAction
        today = timezone.now().date()
        return GitHubFollowAction.objects.filter(
            user=user,
            action_type='follow',
            created_at__date=today
        ).count()
    
    @classmethod
    def get_follow_date(cls, user, target_username):
        """Get when we started following a user"""
        from users.models import GitHubFollowAction
        try:
            action = GitHubFollowAction.objects.filter(
                user=user,
                target_username=target_username,
                action_type='follow'
            ).order_by('-created_at').first()
            return action.created_at if action else None
        except:
            return None
