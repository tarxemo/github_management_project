import graphene
from poutryapp.queries import Query
from poutryapp.mutations import Mutation

class RootQuery(Query, graphene.ObjectType):
    pass

class RootMutation(Mutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=RootQuery, mutation=RootMutation)