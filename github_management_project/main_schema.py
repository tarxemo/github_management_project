import graphene
from github_management.schema import Query as GitHubManagementQuery
from badges.schema import Query as BadgesQuery
from graphql_auth.schema import UserQuery, MeQuery
from graphql_auth import mutations

class Query(GitHubManagementQuery, BadgesQuery, UserQuery, MeQuery, graphene.ObjectType):
    pass

class Mutation(mutations.AuthMutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)