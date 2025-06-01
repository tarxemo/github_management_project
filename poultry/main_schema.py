import graphene
from poutryapp.schema import Query
from poutryapp.views import Mutation

class RootQuery(Query, graphene.ObjectType):
    pass

class RootMutation(Mutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=RootQuery, mutation=RootMutation)