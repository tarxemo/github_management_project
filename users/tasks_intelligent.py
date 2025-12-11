# users/tasks_intelligent.py
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging
from users.models import User
from users.services.intelligent_follow_service import IntelligentFollowService
from github_management.models import GitHubFollowAction

logger = logging.getLogger(__name__)

@shared_task(bind=True, name="users.tasks.intelligent_follow_scheduler")
def intelligent_follow_scheduler(self):
    """
    Scheduled task to run intelligent follow/unfollow for all users who have it enabled
    """
    logger.info("Starting intelligent follow scheduler")
    
    # Get users who have intelligent follow enabled and have GitHub tokens
    users_to_process = User.objects.filter(
        intelligent_follow_enabled=True,
        github_access_token__isnull=False
    ).exclude(github_access_token='')
    
    processed_count = 0
    success_count = 0
    
    for user in users_to_process:
        try:
            # Check if it's time to run for this user based on their schedule
            if not should_run_for_user(user):
                continue
            
            logger.info(f"Running intelligent follow for user: {user.email}")
            
            # Run intelligent follow
            follow_result = IntelligentFollowService.intelligent_follow_users(user)
            
            # Record the action - using existing model structure
            from github_management.models import GitHubUser
            try:
                placeholder_user, _ = GitHubUser.objects.get_or_create(
                    github_username="scheduled_run",
                    defaults={
                        'country': GitHubUser.objects.first().country if GitHubUser.objects.exists() else None
                    }
                )
                GitHubFollowAction.objects.create(
                    user=user,
                    github_user=placeholder_user,
                    status='followed_back' if follow_result['success'] else 'pending'
                )
            except:
                pass  # Skip recording if we can't create placeholder
            
            # Run intelligent unfollow (if follow was successful)
            unfollow_result = {"success": False, "message": "Skipped"}
            if follow_result['success']:
                unfollow_result = IntelligentFollowService.intelligent_unfollow_non_followers(user)
                
                # Record the unfollow action
                try:
                    placeholder_user, _ = GitHubUser.objects.get_or_create(
                        github_username="scheduled_unfollow",
                        defaults={
                            'country': GitHubUser.objects.first().country if GitHubUser.objects.exists() else None
                        }
                    )
                    GitHubFollowAction.objects.create(
                        user=user,
                        github_user=placeholder_user,
                        status='followed_back' if unfollow_result['success'] else 'pending'
                    )
                except:
                    pass  # Skip recording if we can't create placeholder
            
            # Update user's last intelligent follow time
            user.last_intelligent_follow = timezone.now()
            user.save()
            
            processed_count += 1
            if follow_result['success'] or unfollow_result['success']:
                success_count += 1
            
            logger.info(f"Completed intelligent follow for {user.email}: "
                       f"Follow: {follow_result.get('message', 'Failed')}, "
                       f"Unfollow: {unfollow_result.get('message', 'Skipped')}")
            
        except Exception as e:
            logger.error(f"Error running intelligent follow for {user.email}: {e}")
            # Record failure
            try:
                placeholder_user, _ = GitHubUser.objects.get_or_create(
                    github_username="scheduled_error",
                    defaults={
                        'country': GitHubUser.objects.first().country if GitHubUser.objects.exists() else None
                    }
                )
                GitHubFollowAction.objects.create(
                    user=user,
                    github_user=placeholder_user,
                    status='not_followed_back'  # Error state
                )
            except:
                pass
    
    logger.info(f"Intelligent follow scheduler completed: "
               f"Processed {processed_count} users, {success_count} successful")
    
    return {
        'processed': processed_count,
        'successful': success_count,
        'timestamp': timezone.now().isoformat()
    }

def should_run_for_user(user):
    """Check if intelligent follow should run for this user based on their schedule"""
    if not user.last_intelligent_follow:
        return True  # Never run before, run now
    
    now = timezone.now()
    last_run = user.last_intelligent_follow
    
    if user.intelligent_follow_schedule == 'daily':
        # Run if last run was more than 24 hours ago
        return (now - last_run) >= timedelta(hours=24)
    
    elif user.intelligent_follow_schedule == 'weekly':
        # Run if last run was more than 7 days ago
        return (now - last_run) >= timedelta(days=7)
    
    elif user.intelligent_follow_schedule == 'manual':
        # Only run manually
        return False
    
    return False

@shared_task(bind=True, name="users.tasks.intelligent_follow_for_user")
def intelligent_follow_for_user(self, user_id):
    """
    Run intelligent follow for a specific user (can be triggered manually)
    """
    try:
        user = User.objects.get(id=user_id)
        
        if not user.github_access_token:
            return {
                'success': False,
                'message': 'User does not have GitHub access token'
            }
        
        if not user.intelligent_follow_enabled:
            return {
                'success': False,
                'message': 'Intelligent follow is not enabled for this user'
            }
        
        # Run intelligent follow
        follow_result = IntelligentFollowService.intelligent_follow_users(user)
        
        # Record the action - using existing model structure
        try:
            from github_management.models import GitHubUser
            placeholder_user, _ = GitHubUser.objects.get_or_create(
                github_username="manual_task",
                defaults={
                    'country': GitHubUser.objects.first().country if GitHubUser.objects.exists() else None
                }
            )
            GitHubFollowAction.objects.create(
                user=user,
                github_user=placeholder_user,
                status='followed_back' if follow_result['success'] else 'pending'
            )
        except:
            pass  # Skip recording if we can't create placeholder
        
        # Update user's last intelligent follow time
        user.last_intelligent_follow = timezone.now()
        user.save()
        
        return follow_result
        
    except User.DoesNotExist:
        return {
            'success': False,
            'message': 'User not found'
        }
    except Exception as e:
        logger.error(f"Error in intelligent_follow_for_user: {e}")
        return {
            'success': False,
            'message': str(e)
        }

@shared_task(bind=True, name="users.tasks.cleanup_old_follow_actions")
def cleanup_old_follow_actions(self):
    """
    Clean up old follow action records (keep last 30 days)
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count = GitHubFollowAction.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old follow action records")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old follow actions: {e}")
        return {
            'success': False,
            'message': str(e)
        }
