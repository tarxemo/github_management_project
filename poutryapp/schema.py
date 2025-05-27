from ast import Store
import graphene
from graphql import GraphQLError

from  .views import Mutation
from .models import ChickenHouse, EggsCollection, HealthRecord, Order, Feedback, CustomUser,Store
from .outputs import (
    ChickenHouseType,
    EggsCollectionType,
    HealthRecordType,
    OrderType,
    FeedbackType,
    StoreType,
    UserType
)


class Query(graphene.ObjectType):

    all_chicken_houses = graphene.List(ChickenHouseType)
    chicken_house = graphene.Field(ChickenHouseType, id=graphene.ID(required=True))


    # all_eggs_collections = graphene.List(EggsCollectionType)
    eggs_collection = graphene.Field(EggsCollectionType, id=graphene.ID(required=True))

   
    all_health_records = graphene.List(HealthRecordType)
    health_record = graphene.Field(HealthRecordType, id=graphene.ID(required=True))

    all_orders = graphene.List(OrderType)
    order = graphene.Field(OrderType, id=graphene.ID(required=True))

    all_feedbacks = graphene.List(FeedbackType)
    feedback = graphene.Field(FeedbackType, id=graphene.ID(required=True))


    all_workers = graphene.List(UserType)
    all_doctors = graphene.List(UserType)
    all_customers = graphene.List(UserType)
    all_stock_managers = graphene.List(UserType)

    me = graphene.Field(UserType)

    all_stores = graphene.List(StoreType)
    store_by_id = graphene.Field(StoreType, id=graphene.ID(required=True))

    all_chicken_houses = graphene.List(ChickenHouseType)
    chicken_house = graphene.Field(ChickenHouseType, id=graphene.ID(required=True))


    all_eggs_collections = graphene.List(
        EggsCollectionType,
        worker_id=graphene.ID(required=False)  # Make it optional
    )
    

    all_users = graphene.List(UserType)

    def resolve_all_users(root, info):
        return CustomUser.objects.all()
    

    all_users_by_role = graphene.List(UserType, role=graphene.String())

    def resolve_all_users_by_role(root, info, role=None):
        if role:
            return CustomUser.objects.filter(role__iexact=role)
        return CustomUser.objects.all()
    
    # Update the resolver with correct parameter name
    def resolve_all_eggs_collections(self, info, **kwargs):
        worker_id = kwargs.get('worker_id')
        user = info.context.user

        queryset = EggsCollection.objects.select_related('worker', 'chickenHouse')
        
        # If worker_id parameter is provided
        if worker_id:
            return queryset.filter(worker_id=worker_id)
        
        # If user is authenticated worker, show only their records
        if user.is_authenticated and user.role == 'worker':
            return queryset.filter(worker=user)
        
        # For admins/managers, return all records
        if user.is_authenticated and user.role in ['admin', 'manager']:
            return queryset.all()
        
        # Default case (unauthenticated)
        return queryset.none()


    def resolve_all_chicken_houses(root, info):
        return ChickenHouse.objects.select_related('worker').all()

    def resolve_chicken_house(root, info, id):
        try:
            return ChickenHouse.objects.select_related('worker').get(pk=id)
        except ChickenHouse.DoesNotExist:
            return None

    def resolve_all_stores(root, info):
        return Store.objects.all()

    def resolve_store_by_id(root, info, id):
        try:
            return Store.objects.get(pk=id)
        except Store.DoesNotExist:
            return None

 

    def resolve_me(self, info):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError("Not logged in!")
        return user




    def resolve_all_chicken_houses(root, info):
        return ChickenHouse.objects.all()

    def resolve_chicken_house(root, info, id):
        return ChickenHouse.objects.get(pk=id)

    def resolve_all_workers(root, info):
        return CustomUser.objects.filter(role='worker')

    def resolve_all_doctors(root, info):
        return CustomUser.objects.filter(role='doctor')

    def resolve_all_customers(root, info):
        return CustomUser.objects.filter(role='customer')

    def resolve_all_stock_managers(root, info):
        return CustomUser.objects.filter(role='stock_manager')
    def resolve_all_eggs_collections(root, info):
        return EggsCollection.objects.all()

    def resolve_eggs_collection(root, info, id):
        return EggsCollection.objects.get(pk=id)

     
    def resolve_all_health_records(root, info):
        return HealthRecord.objects.all()

    def resolve_health_record(root, info, id):
        return HealthRecord.objects.get(pk=id)

    def resolve_all_orders(root, info):
        return Order.objects.all()

    def resolve_order(root, info, id):
        return Order.objects.get(pk=id)

    def resolve_all_feedbacks(root, info):
        return Feedback.objects.all()

    def resolve_feedback(root, info, id):
        return Feedback.objects.get(pk=id)


schema = graphene.Schema(query=Query, mutation=Mutation)
