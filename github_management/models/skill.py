# github_management/models_skill.py
from django.db import models
from django.conf import settings
from django.utils import timezone


class DeveloperSkill(models.Model):
    """Model to store inferred developer skills from repositories."""
    
    class SkillLevel(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'
        EXPERT = 'expert', 'Expert'
    
    class SkillCategory(models.TextChoices):
        LANGUAGE = 'language', 'Programming Language'
        FRAMEWORK = 'framework', 'Framework'
        LIBRARY = 'library', 'Library'
        TOOL = 'tool', 'Tool'
        PLATFORM = 'platform', 'Platform'
        DATABASE = 'database', 'Database'
        OTHER = 'other', 'Other'
    
    # User relationship (can link to User or GitHubUser)
    github_username = models.CharField(max_length=100, db_index=True)
    
    # Skill information
    skill_name = models.CharField(max_length=100, db_index=True)
    skill_category = models.CharField(
        max_length=20,
        choices=SkillCategory.choices,
        default=SkillCategory.OTHER
    )
    
    # Proficiency metrics
    skill_level = models.CharField(
        max_length=20,
        choices=SkillLevel.choices,
        default=SkillLevel.BEGINNER
    )
    proficiency_score = models.FloatField(default=0.0)  # 0-100 scale
    
    # Evidence metrics
    repo_count = models.PositiveIntegerField(default=0)  # Number of repos using this skill
    total_stars = models.PositiveIntegerField(default=0)  # Total stars across repos with this skill
    total_commits = models.PositiveIntegerField(default=0)  # Estimated commits in this skill
    lines_of_code = models.PositiveIntegerField(default=0)  # Estimated LOC
    
    # Timestamps
    first_used = models.DateTimeField(null=True, blank=True)  # First repo with this skill
    last_used = models.DateTimeField(null=True, blank=True)  # Most recent repo with this skill
    computed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Developer Skill'
        verbose_name_plural = 'Developer Skills'
        unique_together = ('github_username', 'skill_name')
        ordering = ['-proficiency_score', '-total_stars']
        indexes = [
            models.Index(fields=['github_username', '-proficiency_score']),
            models.Index(fields=['skill_name', '-proficiency_score']),
            models.Index(fields=['skill_category', '-proficiency_score']),
        ]
    
    def __str__(self):
        return f"{self.github_username} - {self.skill_name} ({self.get_skill_level_display()})"
    
    def compute_proficiency(self):
        """
        Compute proficiency score based on various metrics.
        Score is 0-100 based on:
        - Number of repos (30%)
        - Total stars (30%)
        - Recency of use (20%)
        - Diversity of use (20%)
        """
        import math
        from datetime import timedelta
        
        # Repo count score (0-30)
        repo_score = min(self.repo_count * 3, 30)
        
        # Stars score (0-30)
        stars_score = min(math.log10(self.total_stars + 1) * 10, 30)
        
        # Recency score (0-20)
        recency_score = 0
        if self.last_used:
            days_since_use = (timezone.now() - self.last_used).days
            if days_since_use < 30:
                recency_score = 20
            elif days_since_use < 90:
                recency_score = 15
            elif days_since_use < 180:
                recency_score = 10
            elif days_since_use < 365:
                recency_score = 5
        
        # Diversity score (0-20) - based on commits and LOC
        diversity_score = min(math.log10(self.total_commits + 1) * 5, 10)
        diversity_score += min(math.log10(self.lines_of_code + 1) * 2, 10)
        
        total_score = repo_score + stars_score + recency_score + diversity_score
        
        # Determine skill level based on score
        if total_score >= 75:
            self.skill_level = self.SkillLevel.EXPERT
        elif total_score >= 50:
            self.skill_level = self.SkillLevel.ADVANCED
        elif total_score >= 25:
            self.skill_level = self.SkillLevel.INTERMEDIATE
        else:
            self.skill_level = self.SkillLevel.BEGINNER
        
        self.proficiency_score = round(total_score, 2)
        return self.proficiency_score
