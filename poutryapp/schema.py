import graphene

from  .views import Mutation
from .models import ChickenHouse, EggsCollection, Assignment, HealthRecord, Order, Feedback, CustomUser
from .outputs import (
    ChickenHouseType,
    EggsCollectionType,
    AssignmentType,
    HealthRecordType,
    OrderType,
    FeedbackType,
    UserType
)


class Query(graphene.ObjectType):

    all_chicken_houses = graphene.List(ChickenHouseType)
    chicken_house = graphene.Field(ChickenHouseType, id=graphene.ID(required=True))


    all_eggs_collections = graphene.List(EggsCollectionType)
    eggs_collection = graphene.Field(EggsCollectionType, id=graphene.ID(required=True))

    all_assignments = graphene.List(AssignmentType)
    assignment = graphene.Field(AssignmentType, id=graphene.ID(required=True))

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

    def resolve_all_assignments(root, info):
        return Assignment.objects.all()

    def resolve_assignment(root, info, id):
        return Assignment.objects.get(pk=id)

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
