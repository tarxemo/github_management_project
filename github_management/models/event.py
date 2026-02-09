# github_management/models_event.py
from django.db import models
from django.conf import settings
from django.utils import timezone


class GitHubEvent(models.Model):
    """Model to track GitHub activity events."""
    
    class EventType(models.TextChoices):
        PUSH = 'PushEvent', 'Push'
        CREATE = 'CreateEvent', 'Create'
        DELETE = 'DeleteEvent', 'Delete'
        FORK = 'ForkEvent', 'Fork'
        WATCH = 'WatchEvent', 'Star'
        PULL_REQUEST = 'PullRequestEvent', 'Pull Request'
        PULL_REQUEST_REVIEW = 'PullRequestReviewEvent', 'PR Review'
        PULL_REQUEST_REVIEW_COMMENT = 'PullRequestReviewCommentEvent', 'PR Review Comment'
        ISSUES = 'IssuesEvent', 'Issue'
        ISSUE_COMMENT = 'IssueCommentEvent', 'Issue Comment'
        COMMIT_COMMENT = 'CommitCommentEvent', 'Commit Comment'
        RELEASE = 'ReleaseEvent', 'Release'
        MEMBER = 'MemberEvent', 'Member'
        PUBLIC = 'PublicEvent', 'Made Public'
        GOLLUM = 'GollumEvent', 'Wiki'
        SPONSORSHIP = 'SponsorshipEvent', 'Sponsorship'
    
    # Event identification
    github_id = models.CharField(max_length=50, unique=True, db_index=True)
    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
        db_index=True
    )
    
    # Actor (who performed the action)
    actor_username = models.CharField(max_length=100, db_index=True)
    actor_id = models.BigIntegerField(null=True, blank=True)
    actor_avatar_url = models.URLField(max_length=500, null=True, blank=True)
    
    # Repository (where it happened)
    repo_name = models.CharField(max_length=512, db_index=True)
    repo_id = models.BigIntegerField(null=True, blank=True)
    
    # Organization (if applicable)
    org_login = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    org_id = models.BigIntegerField(null=True, blank=True)
    
    # Event details (stored as JSON for flexibility)
    payload = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    github_created_at = models.DateTimeField(db_index=True)
    fetched_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Public/private
    is_public = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'GitHub Event'
        verbose_name_plural = 'GitHub Events'
        ordering = ['-github_created_at']
        indexes = [
            models.Index(fields=['actor_username', '-github_created_at']),
            models.Index(fields=['repo_name', '-github_created_at']),
            models.Index(fields=['event_type', '-github_created_at']),
            models.Index(fields=['-github_created_at']),
        ]
    
    def __str__(self):
        return f"{self.actor_username} - {self.get_event_type_display()} - {self.repo_name}"
    
    @property
    def event_summary(self):
        """Generate a human-readable summary of the event."""
        summaries = {
            'PushEvent': f"pushed to {self.repo_name}",
            'CreateEvent': f"created {self.payload.get('ref_type', 'something')} in {self.repo_name}",
            'ForkEvent': f"forked {self.repo_name}",
            'WatchEvent': f"starred {self.repo_name}",
            'PullRequestEvent': f"{self.payload.get('action', 'updated')} a pull request in {self.repo_name}",
            'IssuesEvent': f"{self.payload.get('action', 'updated')} an issue in {self.repo_name}",
            'ReleaseEvent': f"released {self.payload.get('release', {}).get('tag_name', 'a version')} in {self.repo_name}",
        }
        return summaries.get(self.event_type, f"performed {self.event_type} on {self.repo_name}")
