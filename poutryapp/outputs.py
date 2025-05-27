from graphene_django import DjangoObjectType
from .models import *
from .models import CustomUser

from django.contrib.auth import get_user_model

import graphene
from graphene_django import DjangoObjectType
from .models import CustomUser

class UserType(DjangoObjectType):
    class Meta:
        model = CustomUser
        fields = ('id', 'phone_number', 'email', 'role', 'is_verified', 'date_joined', 'last_login')


CustomUser = get_user_model()

class UserType(DjangoObjectType):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'phone_number', 'role', 'first_name', 'last_name')
class RegisterOutput(graphene.ObjectType):
    success = graphene.Boolean(required=True)
    errors = graphene.String()
    user = graphene.Field(UserType)

class LoginOutput(graphene.ObjectType):
    success = graphene.Boolean(required=True)
    errors = graphene.String()
    user = graphene.Field(UserType)
    token = graphene.String(description="JWT access token")
    refresh_token = graphene.String(description="JWT refresh token")

class WorkerType(DjangoObjectType):
    class Meta:
        model = CustomUser
        fields = ('id', 'first_name', 'last_name', 'email', 'phone_number')


class ChickenHouseType(DjangoObjectType):
    class Meta:
        model = ChickenHouse
        fields = ('id', 'name', 'location', 'capacity', 'worker')



class EggsCollectionType(DjangoObjectType):
    class Meta:
        model = EggsCollection
        fields = "__all__"


 

class HealthRecordType(DjangoObjectType):
    class Meta:
        model = HealthRecord
        fields = "__all__"


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = "__all__"


class FeedbackType(DjangoObjectType):
    class Meta:
        model = Feedback
        fields = "__all__"



class UserType(DjangoObjectType):
    class Meta:
        model = CustomUser
        fields = "__all__"


class StoreType(DjangoObjectType):
    class Meta:
        model = Store
        fields = "__all__"