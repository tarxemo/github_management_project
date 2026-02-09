import logging
import math
from django.db.models import Q
from github_management.models import GitHubUser, DeveloperSkill, GitHubRepository

logger = logging.getLogger(__name__)

class DeveloperMatchService:
    """Service for finding compatible developer matches for collaboration."""
    
    @classmethod
    def find_matches(cls, username, limit=10):
        """Find the most compatible developers for a given user."""
        try:
            target_user = GitHubUser.objects.filter(github_username=username).first()
            if not target_user:
                return []
                
            # 1. Get user's top skills
            user_skills = DeveloperSkill.objects.filter(
                github_username=username,
                skill_category=DeveloperSkill.SkillCategory.LANGUAGE
            ).order_by('-proficiency_score')[:3]
            
            skill_names = [s.skill_name for s in user_skills]
            if not skill_names:
                return []
                
            # 2. Find others with similar or complementary skills
            # For now, we'll look for similar skills in same location OR top users globally
            candidates = GitHubUser.objects.exclude(github_username=username)
            
            # Boost if same country
            if target_user.country:
                country_boost = candidates.filter(country=target_user.country)
                if country_boost.count() > 50:
                    candidates = country_boost
            
            # Filter by matching at least one top skill
            candidates = candidates.filter(
                github_username__in=DeveloperSkill.objects.filter(
                    skill_name__in=skill_names
                ).values_list('github_username', flat=True)
            )
            
            # Fetch a pool of candidates to rank
            pool = list(candidates.order_by('-intelligence_score')[:100])
            
            # 3. Score candidates
            matches = []
            for cand in pool:
                score = cls.calculate_match_score(target_user, cand, user_skills)
                matches.append({
                    'user': cand,
                    'match_score': score,
                    'common_skills': list(DeveloperSkill.objects.filter(
                        github_username=cand.github_username,
                        skill_name__in=skill_names
                    ).values_list('skill_name', flat=True))
                })
                
            # Sort by score and return limited
            matches.sort(key=lambda x: x['match_score'], reverse=True)
            return matches[:limit]
            
        except Exception as e:
            logger.error(f"Error finding matches for {username}: {e}")
            return []

    @classmethod
    def calculate_match_score(cls, user1, user2, user1_skills):
        """Calculate a compatibility score between 0-100."""
        score = 0
        
        # Skill compatibility (up to 50 points)
        u2_skills = DeveloperSkill.objects.filter(github_username=user2.github_username)
        u2_skill_names = {s.skill_name: s.proficiency_score for s in u2_skills}
        
        match_count = 0
        for s1 in user1_skills:
            if s1.skill_name in u2_skill_names:
                match_count += 1
                # Similar proficiency is good for peers, different is good for mentor/mentee
                # For now, just match count
                score += 15
        
        # Location proximity (up to 20 points)
        if user1.country == user2.country:
            score += 20
        
        # Activity level compatibility (up to 20 points)
        activity_diff = abs(user1.intelligence_score - user2.intelligence_score)
        if activity_diff < 1.0:
            score += 20
        elif activity_diff < 3.0:
            score += 10
            
        # Experience level (up to 10 points)
        if user1.github_created_at and user2.github_created_at:
            age_diff = abs((user1.github_created_at - user2.github_created_at).days) / 365.0
            if age_diff < 2:
                score += 10
                
        return min(score, 100)
