import graphene
from graphene import InputObjectType



class ChickenHouseInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    location = graphene.String()
    capacity = graphene.Int(required=True)
    worker_ids = graphene.List(graphene.ID, required=True)  # list of worker IDs


class EggsCollectionInput(InputObjectType):
    worker_id = graphene.ID(required=True)
    chicken_house_id = graphene.ID(required=True)
    date_collected = graphene.Date(required=True)
    quantity = graphene.Int(required=True)


class AssignmentInput(InputObjectType):
    worker_id = graphene.ID(required=True)
    chicken_house_id = graphene.ID(required=True)


class HealthRecordInput(InputObjectType):
    doctor_id = graphene.ID(required=True)
    chicken_house_id = graphene.ID(required=True)
    date = graphene.Date(required=True)
    health_issue = graphene.String(required=True)
    treatment = graphene.String(required=True)
    deaths = graphene.Int(required=True)


class OrderInput(InputObjectType):
    customer_id = graphene.ID(required=True)
    product_id = graphene.ID(required=True)
    quantity = graphene.Int(required=True)


class FeedbackInput(InputObjectType):
    customer_id = graphene.ID(required=True)
    order_id = graphene.ID(required=True)
    rating = graphene.Int(required=True)
    comment = graphene.String(required=True)


class RegisterInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    phone_number = graphene.String(required=True)
    email = graphene.String()
    password = graphene.String(required=True)

class LoginInput(graphene.InputObjectType):
    phone_number = graphene.String(required=True)
    password = graphene.String(required=True)
