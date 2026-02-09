import graphene
from graphene_django import DjangoObjectType
from .models import (
    GitHubUser, GitHubRepository, GitHubOrganization, 
    GitHubEvent, DeveloperSkill, Leaderboard, LeaderboardEntry, GrowthAnalytics
)

class GitHubUserType(DjangoObjectType):
    class Meta:
        model = GitHubUser
        fields = "__all__"

class GitHubRepositoryType(DjangoObjectType):
    class Meta:
        model = GitHubRepository
        fields = "__all__"

class GitHubOrganizationType(DjangoObjectType):
    class Meta:
        model = GitHubOrganization
        fields = "__all__"

class GitHubEventType(DjangoObjectType):
    class Meta:
        model = GitHubEvent
        fields = "__all__"

class DeveloperSkillType(DjangoObjectType):
    class Meta:
        model = DeveloperSkill
        fields = "__all__"

class LeaderboardType(DjangoObjectType):
    class Meta:
        model = Leaderboard
        fields = "__all__"

class LeaderboardEntryType(DjangoObjectType):
    class Meta:
        model = LeaderboardEntry
        fields = "__all__"

class GrowthAnalyticsType(DjangoObjectType):
    class Meta:
        model = GrowthAnalytics
        fields = "__all__"

class Query(graphene.ObjectType):
    # User Queries
    github_user = graphene.Field(GitHubUserType, username=graphene.String(required=True))
    all_github_users = graphene.List(GitHubUserType)
    
    # Repository Queries
    repositories = graphene.List(GitHubRepositoryType, username=graphene.String())
    trending_repositories = graphene.List(GitHubRepositoryType, limit=graphene.Int())
    
    # Leaderboard Queries
    leaderboard = graphene.Field(
        LeaderboardType, 
        type=graphene.String(required=True),
        country_slug=graphene.String(),
        language=graphene.String()
    )
    
    # Discovery Queries
    recommended_developers = graphene.List(GitHubUserType, username=graphene.String(required=True))
    
    def resolve_github_user(self, info, username):
        return GitHubUser.objects.filter(github_username=username).first()
    
    def resolve_all_github_users(self, info):
        return GitHubUser.objects.all()
    
    def resolve_repositories(self, info, username=None):
        if username:
            return GitHubRepository.objects.filter(owner_username=username)
        return GitHubRepository.objects.all()
    
    def resolve_trending_repositories(self, info, limit=10):
        return GitHubRepository.objects.order_by('-stargazers_count')[:limit]
        
    def resolve_leaderboard(self, info, type, country_slug=None, language=None):
        return Leaderboard.objects.filter(
            leaderboard_type=type,
            country_slug=country_slug,
            language=language
        ).first()

    def resolve_recommended_developers(self, info, username):
        from .services.developer_match_service import DeveloperMatchService
        matches = DeveloperMatchService.find_matches(username)
        return [m['user'] for m in matches]
