import graphene
from graphene_django import DjangoObjectType
from .models import Achievement, UserAchievement

class AchievementType(DjangoObjectType):
    class Meta:
        model = Achievement
        fields = "__all__"

class UserAchievementType(DjangoObjectType):
    class Meta:
        model = UserAchievement
        fields = "__all__"

class Query(graphene.ObjectType):
    all_achievements = graphene.List(AchievementType)
    user_achievements = graphene.List(UserAchievementType, username=graphene.String(required=True))
    
    def resolve_all_achievements(self, info):
        return Achievement.objects.filter(is_active=True)
        
    def resolve_user_achievements(self, info, username):
        return UserAchievement.objects.filter(user__github_username=username, is_unlocked=True)
