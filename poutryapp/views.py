from django.forms import ValidationError
import graphql_jwt
from rest_framework import viewsets
from .models import Product
from .serializers import ProductSerializer
import graphene
from .models import *
from .inputs import *
from .outputs import *
from django.contrib.auth import authenticate
from .inputs import RegisterInput, LoginInput
from .outputs import UserType
from .inputs import ChickenHouseInput
from .outputs import ChickenHouseType
 
from graphql import GraphQLError
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from .inputs import RegisterInput
from .outputs import RegisterOutput, LoginOutput
from .models import CustomUser
 

class RegisterMutation(graphene.Mutation):
    class Arguments:
        input = RegisterInput(required=True)
    
    Output = RegisterOutput

    @classmethod
    def mutate(cls, root, info, input):
        try:
            # Convert Graphene input to dict and validate
            input_dict = {
                'phone_number': input.phone_number,
                'password': input.password,
                'email': input.email,
                # 'date_of_birth': input.date_of_birth
            }
            validate_register_input(input_dict)
            
            # Create user with default 'customer' role
            user = CustomUser.objects.create_user(
                phone_number=input.phone_number,
                email=input.email,
                password=input.password,
                role='customer',  # Set default role here
                # date_of_birth=input.date_of_birth
            )
            
            # Add to customer group
            group, _ = Group.objects.get_or_create(name='customer')
            user.groups.add(group)
            
            return RegisterOutput(
                success=True,
                user=user,
                errors=None
            )
            
        except ValidationError as e:
            error_messages = []
            for field, messages in e.message_dict.items():
                error_messages.extend([f"{field}: {msg}" for msg in messages])
            
            return RegisterOutput(
                success=False,
                errors="; ".join(error_messages),
                user=None
            )
        

from rest_framework_simplejwt.tokens import RefreshToken
from graphql import GraphQLError

from rest_framework_simplejwt.tokens import RefreshToken

class LoginMutation(graphene.Mutation):
    class Arguments:
        input = LoginInput(required=True)
    
    Output = LoginOutput

    @classmethod
    def mutate(cls, root, info, input):
        try:
            # Authenticate user
            user = authenticate(
                request=info.context,
                phone_number=input.phone_number,
                password=input.password
            )
            
            if user is None:
                raise GraphQLError("Invalid phone number or password")
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Add role to the token's payload
            refresh["role"] = user.role  # Include role in the payload
            
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Login the user (optional - only needed if using session auth)
            login(info.context, user)
            
            return LoginOutput(
                success=True,
                user=user,
                token=access_token,
                refresh_token=refresh_token,
                errors=None
            )
            
        except Exception as e:
            return LoginOutput(
                success=False,
                errors=str(e),
                user=None,
                token=None,
                refresh_token=None
            )







class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer



# Create

class CreateChickenHouse(graphene.Mutation):
    class Arguments:
        input = ChickenHouseInput(required=True)

    chicken_house = graphene.Field(ChickenHouseType)

    def mutate(self, info, input):
        # user = info.context.user
        
        # Check if user is authenticated and is admin
        # if not user.is_authenticated or user.is_admin:
        #     raise Exception("Only admins can create chicken houses.")

        # Proceed to create the chicken house
        chicken_house = ChickenHouse.objects.create(
            name=input.name,
            location=input.location,
            capacity=input.capacity
        )

        # Assign workers (if worker_ids are passed)
        for worker_id in input.worker_ids:
            worker = CustomUser.objects.get(id=worker_id, role='worker')
            Assignment.objects.create(worker=worker, chicken_house=chicken_house)

        return CreateChickenHouse(chicken_house=chicken_house)

# Update
class UpdateChickenHouse(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = ChickenHouseInput(required=True)

    chicken_house = graphene.Field(ChickenHouseType)

    def mutate(self, info, id, input):
        user = info.context.user
        if not user.is_authenticated or user.role != 'admin':
            raise Exception("Only admins can update chicken houses.")

        house = ChickenHouse.objects.get(pk=id)
        house.name = input.name
        house.location = input.location
        house.capacity = input.capacity
        house.save()


        # Remove existing assignments
        Assignment.objects.filter(chicken_house=house).delete()

        for worker_id in input.worker_ids:
            worker = CustomUser.objects.get(id=worker_id)
            if worker.role != 'worker':
                raise Exception(f"User {worker_id} is not a worker.")
            if Assignment.objects.filter(worker=worker).exists():
                raise Exception(f"Worker {worker.name} is already assigned elsewhere.")
            Assignment.objects.create(worker=worker, chicken_house=house)

        return UpdateChickenHouse(chicken_house=house)

# Delete
class DeleteChickenHouse(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        user = info.context.user
        if not user.is_authenticated or user.role != 'admin':
            raise Exception("Only admins can delete chicken houses.")

        house = ChickenHouse.objects.get(pk=id)
        house.delete()
        return DeleteChickenHouse(ok=True)


# Eggs Collection
class CreateEggsCollection(graphene.Mutation):
    class Arguments:
        input = EggsCollectionInput(required=True)

    collection = graphene.Field(EggsCollectionType)

    def mutate(self, info, input):
        worker = CustomUser.objects.get(pk=input.worker_id)
        chicken_house = ChickenHouse.objects.get(pk=input.chicken_house_id)

        collection = EggsCollection.objects.create(
            worker=worker,
            chicken_house=chicken_house,
            date_collected=input.date_collected,
            quantity=input.quantity
        )
        return CreateEggsCollection(collection=collection)


class UpdateEggsCollection(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = EggsCollectionInput(required=True)

    collection = graphene.Field(EggsCollectionType)

    def mutate(self, info, id, input):
        collection = EggsCollection.objects.get(pk=id)
        collection.worker = CustomUser.objects.get(pk=input.worker_id)
        collection.chicken_house = ChickenHouse.objects.get(pk=input.chicken_house_id)
        collection.date_collected = input.date_collected
        collection.quantity = input.quantity
        collection.save()
        return UpdateEggsCollection(collection=collection)


class DeleteEggsCollection(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        try:
            collection = EggsCollection.objects.get(pk=id)
            collection.delete()
            return DeleteEggsCollection(ok=True)
        except EggsCollection.DoesNotExist:
            return DeleteEggsCollection(ok=False)


# Assignment
class CreateAssignment(graphene.Mutation):
    class Arguments:
        input = AssignmentInput(required=True)

    assignment = graphene.Field(AssignmentType)

    def mutate(self, info, input):
        worker = CustomUser.objects.get(pk=input.worker_id)
        chicken_house = ChickenHouse.objects.get(pk=input.chicken_house_id)
        assignment = Assignment.objects.create(worker=worker, chicken_house=chicken_house)
        return CreateAssignment(assignment=assignment)


class UpdateAssignment(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = AssignmentInput(required=True)

    assignment = graphene.Field(AssignmentType)

    def mutate(self, info, id, input):
        assignment = Assignment.objects.get(pk=id)
        assignment.worker = CustomUser.objects.get(pk=input.worker_id)
        assignment.chicken_house = ChickenHouse.objects.get(pk=input.chicken_house_id)
        assignment.save()
        return UpdateAssignment(assignment=assignment)


class DeleteAssignment(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        try:
            assignment = Assignment.objects.get(pk=id)
            assignment.delete()
            return DeleteAssignment(ok=True)
        except Assignment.DoesNotExist:
            return DeleteAssignment(ok=False)


# Health Record
class CreateHealthRecord(graphene.Mutation):
    class Arguments:
        input = HealthRecordInput(required=True)

    record = graphene.Field(HealthRecordType)

    def mutate(self, info, input):
        doctor = CustomUser.objects.get(pk=input.doctor_id)
        chicken_house = ChickenHouse.objects.get(pk=input.chicken_house_id)
        record = HealthRecord.objects.create(
            doctor=doctor,
            chicken_house=chicken_house,
            date=input.date,
            health_issue=input.health_issue,
            treatment=input.treatment,
            deaths=input.deaths
        )
        return CreateHealthRecord(record=record)


class UpdateHealthRecord(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = HealthRecordInput(required=True)

    record = graphene.Field(HealthRecordType)

    def mutate(self, info, id, input):
        record = HealthRecord.objects.get(pk=id)
        record.doctor = CustomUser.objects.get(pk=input.doctor_id)
        record.chicken_house = ChickenHouse.objects.get(pk=input.chicken_house_id)
        record.date = input.date
        record.health_issue = input.health_issue
        record.treatment = input.treatment
        record.deaths = input.deaths
        record.save()
        return UpdateHealthRecord(record=record)


class DeleteHealthRecord(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        try:
            record = HealthRecord.objects.get(pk=id)
            record.delete()
            return DeleteHealthRecord(ok=True)
        except HealthRecord.DoesNotExist:
            return DeleteHealthRecord(ok=False)


# Order
class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)

    def mutate(self, info, input):
        customer = CustomUser.objects.get(pk=input.customer_id)
        product = Product.objects.get(pk=input.product_id)
        order = Order.objects.create(
            customer=customer,
            product=product,
            quantity=input.quantity
        )
        return CreateOrder(order=order)


class UpdateOrder(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)

    def mutate(self, info, id, input):
        order = Order.objects.get(pk=id)
        order.customer = CustomUser.objects.get(pk=input.customer_id)
        order.product = Product.objects.get(pk=input.product_id)
        order.quantity = input.quantity
        order.save()
        return UpdateOrder(order=order)


class DeleteOrder(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        try:
            order = Order.objects.get(pk=id)
            order.delete()
            return DeleteOrder(ok=True)
        except Order.DoesNotExist:
            return DeleteOrder(ok=False)


# Feedback
class CreateFeedback(graphene.Mutation):
    class Arguments:
        input = FeedbackInput(required=True)

    feedback = graphene.Field(FeedbackType)

    def mutate(self, info, input):
        customer = CustomUser.objects.get(pk=input.customer_id)
        order = Order.objects.get(pk=input.order_id)
        feedback = Feedback.objects.create(
            customer=customer,
            order=order,
            rating=input.rating,
            comment=input.comment
        )
        return CreateFeedback(feedback=feedback)


class UpdateFeedback(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = FeedbackInput(required=True)

    feedback = graphene.Field(FeedbackType)

    def mutate(self, info, id, input):
        feedback = Feedback.objects.get(pk=id)
        feedback.customer = CustomUser.objects.get(pk=input.customer_id)
        feedback.order = Order.objects.get(pk=input.order_id)
        feedback.rating = input.rating
        feedback.comment = input.comment
        feedback.save()
        return UpdateFeedback(feedback=feedback)


class DeleteFeedback(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        try:
            feedback = Feedback.objects.get(pk=id)
            feedback.delete()
            return DeleteFeedback(ok=True)
        except Feedback.DoesNotExist:
            return DeleteFeedback(ok=False)

class RegisterUser(graphene.Mutation):
    class Arguments:
        input = RegisterInput(required=True)

    user = graphene.Field(UserType)

    def mutate(self, info, input):
        if CustomUser.objects.filter(phone_number=input.phone_number).exists():
            raise Exception("User with this phone number already exists")

        # Force role to 'customer' on registration
        user = CustomUser.objects.create_user(
            phone_number=input.phone_number,
            password=input.password,
            name=input.name,
            role='customer',  # Default role enforced
            email=input.email,
        )
        return RegisterUser(user=user)
    

 
import graphql_jwt
import graphene
from django.contrib.auth import authenticate
from .outputs import UserType
from .inputs import LoginInput

from graphql_jwt.utils import jwt_payload, jwt_encode
class LoginUser(graphene.Mutation):
    class Arguments:
        input = LoginInput(required=True)

    user = graphene.Field(UserType)
    token = graphene.String()

    def mutate(self, info, input):
        user = authenticate(phone_number=input.phone_number, password=input.password)
        if not user:
            raise Exception("Invalid credentials")

        payload = jwt_payload(user)
        payload['role'] = user.role  # 👈 Add this line
        token = jwt_encode(payload)

        return LoginUser(user=user, token=token)


# Root Mutation
class Mutation(graphene.ObjectType):

  

    register = RegisterMutation.Field()
    login = LoginMutation.Field()


    # JWT Authentication
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    verify_token = graphql_jwt.Verify.Field()

    create_chicken_house = CreateChickenHouse.Field()
    update_chicken_house = UpdateChickenHouse.Field()
    delete_chicken_house = DeleteChickenHouse.Field()

    create_eggs_collection = CreateEggsCollection.Field()
    update_eggs_collection = UpdateEggsCollection.Field()
    delete_eggs_collection = DeleteEggsCollection.Field()

    create_assignment = CreateAssignment.Field()
    update_assignment = UpdateAssignment.Field()
    delete_assignment = DeleteAssignment.Field()

    create_health_record = CreateHealthRecord.Field()
    update_health_record = UpdateHealthRecord.Field()
    delete_health_record = DeleteHealthRecord.Field()

    create_order = CreateOrder.Field()
    update_order = UpdateOrder.Field()
    delete_order = DeleteOrder.Field()

    create_feedback = CreateFeedback.Field()
    update_feedback = UpdateFeedback.Field()
    delete_feedback = DeleteFeedback.Field()
