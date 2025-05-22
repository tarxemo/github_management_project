from graphene_django import DjangoObjectType
from .models import *
from .models import CustomUser

 

class ChickenHouseType(DjangoObjectType):
    class Meta:
        model = ChickenHouse



class EggsCollectionType(DjangoObjectType):
    class Meta:
        model = EggsCollection
        fields = "__all__"


class AssignmentType(DjangoObjectType):
    class Meta:
        model = Assignment
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