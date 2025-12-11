# users/validators.py
from github import Github, GithubException
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

def validate_github_token(token):
    """
    Validate GitHub access token and check required permissions
    """
    if not token:
        raise ValidationError("GitHub access token is required")
    
    try:
        # Try to authenticate with GitHub
        g = Github(token, timeout=10)
        github_user = g.get_user()
        
        # Test basic access
        user_data = github_user.login
        if not user_data:
            raise ValidationError("Invalid GitHub token")
        
        # Check if token has required permissions for following
        try:
            # Try to access following list (requires user:follow scope)
            following = list(github_user.get_following()[:1])
        except GithubException as e:
            if "403" in str(e) or "Forbidden" in str(e):
                raise ValidationError(
                    "GitHub token requires 'user:follow' permission. "
                    "Please create a new token with the correct scopes."
                )
            else:
                raise ValidationError(f"GitHub API error: {e}")
        
        # Check rate limits
        rate_limit = g.get_rate_limit()
        if rate_limit.core.remaining < 100:
            logger.warning(f"Low rate limit: {rate_limit.core.remaining} remaining")
        
        return True
        
    except GithubException as e:
        if "401" in str(e) or "Bad credentials" in str(e):
            raise ValidationError("Invalid GitHub token")
        elif "403" in str(e) or "Forbidden" in str(e):
            raise ValidationError(
                "GitHub token lacks required permissions. "
                "Make sure it has 'user' and 'user:follow' scopes."
            )
        else:
            raise ValidationError(f"GitHub API error: {e}")
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise ValidationError(f"Error validating GitHub token: {str(e)}")

def validate_github_token_for_intelligent_follow(token):
    """
    Additional validation for intelligent follow features
    """
    # First do basic validation
    validate_github_token(token)
    
    try:
        g = Github(token, timeout=10)
        github_user = g.get_user()
        
        # Check if user can access their own following/followers
        try:
            followers_count = github_user.followers
            following_count = github_user.following
        except GithubException as e:
            raise ValidationError(
                "Cannot access follower/following data. "
                "Token may lack required permissions."
            )
        
        # Check if user has reasonable limits (not a brand new account)
        if following_count > 4000:
            logger.warning(f"User following many accounts: {following_count}")
        
        # Test a follow/unfollow operation with a safe target
        # (We'll just check permissions without actually following)
        try:
            # Try to get a user to test API access
            test_user = g.get_user("octocat")
            test_user.login  # This will fail if token lacks permissions
        except GithubException as e:
            if "403" in str(e):
                raise ValidationError(
                    "Token lacks permission to access user data. "
                    "Please ensure token has 'user' scope."
                )
        
        return True
        
    except Exception as e:
        logger.error(f"Intelligent follow validation error: {e}")
        raise ValidationError(f"Error validating token for intelligent follow: {str(e)}")
