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
from .outputs import ChickenHouseType
 
from graphql import GraphQLError
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from .inputs import RegisterInput
from .outputs import RegisterOutput, LoginOutput
from .models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken
from graphql import GraphQLError

from rest_framework_simplejwt.tokens import RefreshToken

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



class UpdateUserMutation(graphene.Mutation):
    class Arguments:
        input = UpdateUserInput(required=True)

    user = graphene.Field(UserType)
    success = graphene.Boolean()
    errors = graphene.String()

    @classmethod
    def mutate(cls, root, info, input):
        try:
            user = CustomUser.objects.get(pk=input.id)

            if input.email:
                user.email = input.email
            if input.phone_number:
                user.phone_number = input.phone_number
            if input.password:
                user.set_password(input.password)
            if input.role:
                user.role = input.role
            if input.first_name:    # New: Update first_name
                user.first_name = input.first_name
            if input.last_name:     # New: Update last_name
                user.last_name = input.last_name

            user.save()
            return UpdateUserMutation(user=user, success=True)
        except CustomUser.DoesNotExist:
            return UpdateUserMutation(success=False, errors="User not found")
        except Exception as e:
            return UpdateUserMutation(success=False, errors=str(e))



class DeleteUserMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    errors = graphene.String()

    @classmethod
    def mutate(cls, root, info, id):
        try:
            user = CustomUser.objects.get(pk=id)
            user.delete()
            return DeleteUserMutation(success=True)
        except CustomUser.DoesNotExist:
            return DeleteUserMutation(success=False, errors="User not found")
        except Exception as e:
            return DeleteUserMutation(success=False, errors=str(e))



class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
  

 
 
    
# Create


class CreateChickenHouse(graphene.Mutation):
    class Arguments:
        input = CreateChickenHouseInput(required=True)

    chicken_house = graphene.Field(ChickenHouseType)

    def mutate(self, info, input):
        worker = CustomUser.objects.get(pk=input.worker_id)

        chicken_house = ChickenHouse.objects.create(
            name=input.name,
            location=input.location or '',
            capacity=input.capacity,
            worker=worker
        )
        return CreateChickenHouse(chicken_house=chicken_house)


class UpdateChickenHouse(graphene.Mutation):
    class Arguments:
        input = UpdateChickenHouseInput(required=True)

    chicken_house = graphene.Field(ChickenHouseType)

    def mutate(self, info, input):
        try:
            chicken_house = ChickenHouse.objects.get(pk=input.id)
        except ChickenHouse.DoesNotExist:
            raise Exception("Chicken house not found")

        if input.name is not None:
            chicken_house.name = input.name
        if input.location is not None:
            chicken_house.location = input.location
        if input.capacity is not None:
            chicken_house.capacity = input.capacity
        if input.worker_id is not None:
            chicken_house.worker = CustomUser.objects.get(pk=input.worker_id)

        chicken_house.save()
        return UpdateChickenHouse(chicken_house=chicken_house)


class DeleteChickenHouse(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        try:
            house = ChickenHouse.objects.get(pk=id)
            house.delete()
            return DeleteChickenHouse(ok=True)
        except ChickenHouse.DoesNotExist:
            return DeleteChickenHouse(ok=False)

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
class CreateStore(graphene.Mutation):
    class Arguments:
        input = StoreInput(required=True)

    store = graphene.Field(StoreType)
    success = graphene.Boolean()
    errors = graphene.String()

    def mutate(self, info, input):
        try:
            store = Store.objects.create(
                entry_type=input.entry_type,
                product_id=input.product_id,
                eggs_collection_id=input.eggs_collection_id,
                quantity=input.quantity,
                unit=input.unit,
                good_eggs=input.good_eggs or 0,
                broken_eggs=input.broken_eggs or 0,
                cracked_eggs=input.cracked_eggs or 0,
                dirty_eggs=input.dirty_eggs or 0,
                quality_checker_id=input.quality_checker_id,
                notes=input.notes or ''
            )
            return CreateStore(store=store, success=True)
        except Exception as e:
            return CreateStore(success=False, errors=str(e))

class UpdateStore(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = StoreInput(required=True)

    store = graphene.Field(StoreType)
    success = graphene.Boolean()
    errors = graphene.String()

    def mutate(self, info, id, input):
        try:
            store = Store.objects.get(pk=id)
            for field, value in input.items():
                if value is not None:
                    setattr(store, field, value)
            store.save()
            return UpdateStore(store=store, success=True)
        except Exception as e:
            return UpdateStore(success=False, errors=str(e))

class DeleteStore(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    errors = graphene.String()

    def mutate(self, info, id):
        try:
            store = Store.objects.get(pk=id)
            store.delete()
            return DeleteStore(success=True)
        except Exception as e:
            return DeleteStore(success=False, errors=str(e))

# ========== SALE ==========

class CreateSale(graphene.Mutation):
    class Arguments:
        input = SaleInput(required=True)

    sale = graphene.Field(SaleType)
    success = graphene.Boolean()
    errors = graphene.String()

    def mutate(self, info, input):
        try:
            sale = Sale.objects.create(
                product_id=input.product_id,
                quantity=input.quantity,
                stock_manager_id=input.stock_manager_id
            )
            return CreateSale(sale=sale, success=True)
        except Exception as e:
            return CreateSale(success=False, errors=str(e))

class UpdateSale(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = SaleInput(required=True)

    sale = graphene.Field(SaleType)
    success = graphene.Boolean()
    errors = graphene.String()

    def mutate(self, info, id, input):
        try:
            sale = Sale.objects.get(pk=id)
            for field, value in input.items():
                if value is not None:
                    setattr(sale, field, value)
            sale.save()
            return UpdateSale(sale=sale, success=True)
        except Exception as e:
            return UpdateSale(success=False, errors=str(e))

class DeleteSale(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    errors = graphene.String()

    def mutate(self, info, id):
        try:
            sale = Sale.objects.get(pk=id)
            sale.delete()
            return DeleteSale(success=True)
        except Exception as e:
            return DeleteSale(success=False, errors=str(e))

# ========== ORDER ==========

class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    errors = graphene.String()

    def mutate(self, info, input):
        try:
            order = Order.objects.create(**input)
            return CreateOrder(order=order, success=True)
        except Exception as e:
            return CreateOrder(success=False, errors=str(e))

class UpdateOrder(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    errors = graphene.String()

    def mutate(self, info, id, input):
        try:
            order = Order.objects.get(pk=id)
            for field, value in input.items():
                if value is not None:
                    setattr(order, field, value)
            order.save()
            return UpdateOrder(order=order, success=True)
        except Exception as e:
            return UpdateOrder(success=False, errors=str(e))

class DeleteOrder(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()
    errors = graphene.String()

    def mutate(self, info, id):
        try:
            order = Order.objects.get(pk=id)
            order.delete()
            return DeleteOrder(success=True)
        except Exception as e:
            return DeleteOrder(success=False, errors=str(e))

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
    update_user = UpdateUserMutation.Field()
    delete_user = DeleteUserMutation.Field()

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

     

    create_health_record = CreateHealthRecord.Field()
    update_health_record = UpdateHealthRecord.Field()
    delete_health_record = DeleteHealthRecord.Field()

     
    create_feedback = CreateFeedback.Field()
    update_feedback = UpdateFeedback.Field()
    delete_feedback = DeleteFeedback.Field()


    create_store = CreateStore.Field()
    update_store = UpdateStore.Field()
    delete_store = DeleteStore.Field()

    create_sale = CreateSale.Field()
    update_sale = UpdateSale.Field()
    delete_sale = DeleteSale.Field()

    create_order = CreateOrder.Field()
    update_order = UpdateOrder.Field()
    delete_order = DeleteOrder.Field()
