import graphene
from graphql import GraphQLError
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import (
    User, ChickenHouse, EggCollection, EggInventory, EggSale,
    FoodType, FoodInventory, FoodPurchase, FoodDistribution,
    Medicine, MedicineInventory, MedicinePurchase, MedicineDistribution,
    ChickenDeathRecord
)
from .outputs import *
from .inputs import *
from datetime import date
from graphql_jwt.shortcuts import get_token, create_refresh_token
import graphql_jwt

UserModel = get_user_model()

class AuthMutation(graphene.Mutation):
    class Arguments:
        phone_number = graphene.String(required=True)
        password = graphene.String(required=True)

    token = graphene.String()
    refresh_token = graphene.String()
    user = graphene.Field(UserOutput)

    @classmethod
    def mutate(cls, root, info, phone_number, password):
        user = UserModel.objects.filter(phone_number=phone_number).first()

        if not user or not user.check_password(password):
            raise GraphQLError("Invalid phone number or password")

        # Generate access and refresh tokens
        access_token = get_token(user)
        refresh_token = create_refresh_token(user)

        return AuthMutation(
            token=access_token,
            refresh_token=refresh_token,
            user=user
        )


class ChangePassword(graphene.Mutation):
    success = graphene.Boolean()
    message = graphene.String()

    class Arguments:
        input = ChangePasswordInput(required=True)

    def mutate(self, info, input):
        user = info.context.user

        if not user.check_password(input.old_password):
            return ChangePassword(success=False, message="Old password is incorrect.")

        user.set_password(input.new_password)
        user.save()

        return ChangePassword(success=True, message="Password changed successfully.")
    
class CreateUser(graphene.Mutation):
    class Arguments:
        input = UserInput(required=True)

    user = graphene.Field(UserOutput)

    @transaction.atomic
    def mutate(self, info, input):
        # Only admin can create users
        if not info.context.user.is_authenticated or info.context.user.user_type != 'ADMIN':
            raise GraphQLError("Only admin can create users")
        
        user = UserModel(
            phone_number=input.phone_number,
            first_name=input.get('first_name', ''),
            last_name=input.get('last_name', ''),
            user_type=input.user_type
        )
        user.set_password(input.password)
        
        # Assign chicken house if worker
        if input.user_type == 'WORKER' and input.chicken_house_id:
            try:
                chicken_house = ChickenHouse.objects.get(pk=input.chicken_house_id)
                # Ensure chicken house doesn't already have a worker
                if UserModel.objects.filter(chicken_house=chicken_house, user_type='WORKER').exists():
                    raise GraphQLError("This chicken house already has an assigned worker")
                user.chicken_house = chicken_house
            except ChickenHouse.DoesNotExist:
                raise GraphQLError("Chicken house not found")
        
        user.save()
        return CreateUser(user=user)

class CreateChickenHouse(graphene.Mutation):
    class Arguments:
        input = ChickenHouseInput(required=True)

    chicken_house = graphene.Field(ChickenHouseOutput)

    def mutate(self, info, input):
        if not info.context.user.is_authenticated or info.context.user.user_type != 'ADMIN':
            raise GraphQLError("Only admin can create chicken houses")
        
        worker = None
        if input.get('worker_id'):
            try:
                worker = User.objects.get(pk=input.worker_id, user_type='WORKER')
            except User.DoesNotExist:
                raise GraphQLError("Worker not found")
        
        chicken_house = ChickenHouse(
            name=input.name,
            capacity=input.capacity,
            is_active=input.get('is_active', True))
        chicken_house.save()
        
        # Assign worker if provided
        if worker:
            worker.chicken_house = chicken_house
            worker.save()
            
        return CreateChickenHouse(chicken_house=chicken_house)

class UpdateChickenHouse(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = ChickenHouseInput(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    chicken_house = graphene.Field(ChickenHouseOutput)

    def mutate(self, info, id, input):
        try:
            house = ChickenHouse.objects.get(pk=id)
        except ChickenHouse.DoesNotExist:
            raise GraphQLError("Chicken house not found.")

        worker = None
        if input.get('worker_id'):
            try:
                worker = User.objects.get(pk=input.worker_id, user_type='WORKER')
            except User.DoesNotExist:
                raise GraphQLError("Worker not found")

        # Clear previous worker assignment
        previous_workers = User.objects.filter(chicken_house=house, user_type='WORKER')
        for prev_worker in previous_workers:
            prev_worker.chicken_house = None
            prev_worker.save()

        # Update house details
        house.name = input.name
        house.capacity = input.capacity
        house.is_active = input.is_active
        house.save()

        # Assign new worker if provided
        if worker:
            worker.chicken_house = house
            worker.save()

        return UpdateChickenHouse(success=True, message="House updated successfully", chicken_house=house)

class AddChickensToHouse(graphene.Mutation):
    class Arguments:
        input = AddChickensInput(required=True)

    chicken_house = graphene.Field(ChickenHouseOutput)

    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.user_type != "ADMIN":
            raise GraphQLError("Only admin can add chickens")

        try:
            house = ChickenHouse.objects.get(pk=input.chicken_house_id)
        except ChickenHouse.DoesNotExist:
            raise GraphQLError("Chicken house not found")

        if house.current_chicken_count + input.number_of_chickens > house.capacity:
            raise GraphQLError("Cannot exceed chicken house capacity")

        house.current_chicken_count += input.number_of_chickens
        house.save()
        return AddChickensToHouse(chicken_house=house)
    
    
class RecordEggCollection(graphene.Mutation):
    class Arguments:
        input = EggCollectionInput(required=True)

    collection = graphene.Field(EggCollectionOutput)

    @transaction.atomic
    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.user_type != 'WORKER':
            raise GraphQLError("Only workers can record egg collections")
        
        try:
            chicken_house = ChickenHouse.objects.get(pk=input.chicken_house_id)
            if user.chicken_house != chicken_house:
                raise GraphQLError("You can only record collections for your assigned chicken house")
            
            collection = EggCollection(
                worker=user,
                chicken_house=chicken_house,
                full_trays=input.full_trays,
                loose_eggs=input.get('loose_eggs', 0),
                rejected_eggs=input.get('rejected_eggs', 0),
                notes=input.get('notes', '')
            )
            collection.save()
            
            # Update inventory (handled by signal)
            return RecordEggCollection(collection=collection)
        except ChickenHouse.DoesNotExist:
            raise GraphQLError("Chicken house not found")

class ConfirmEggCollection(graphene.Mutation):
    class Arguments:
        input = EggCollectionConfirmationInput(required=True)

    collection = graphene.Field(EggCollectionOutput)

    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.user_type != 'STOCK_MANAGER':
            raise GraphQLError("Only stock managers can confirm egg collections")
        
        try:
            collection = EggCollection.objects.get(pk=input.collection_id)
            if collection.stock_manager_confirmed:
                raise GraphQLError("This collection has already been confirmed")
            
            collection.stock_manager_confirmed = input.confirmed
            collection.save()
            
            return ConfirmEggCollection(collection=collection)
        except EggCollection.DoesNotExist:
            raise GraphQLError("Egg collection not found")

class RecordEggSale(graphene.Mutation):
    class Arguments:
        input = EggSaleInput(required=True)

    sale = graphene.Field(EggSaleOutput)
    inventory = graphene.Field(EggInventoryOutput)

    @transaction.atomic
    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.user_type != 'STOCK_MANAGER':
            raise GraphQLError("Only stock managers can record egg sales")
        
        inventory = EggInventory.objects.first()
        if not inventory or inventory.total_eggs < input.quantity:
            raise GraphQLError("Not enough eggs in inventory for this sale")
        
        sale = EggSale(
            quantity=input.quantity,
            price_per_egg=input.price_per_egg,
            buyer_name=input.buyer_name,
            buyer_contact=input.get('buyer_contact', ''),
            recorded_by=user
        )
        sale.save()
        
        return RecordEggSale(sale=sale, inventory=EggInventory.objects.first())

class CreateFoodType(graphene.Mutation):
    class Arguments:
        input = FoodTypeInput(required=True)

    food_type = graphene.Field(FoodTypeOutput)

    def mutate(self, info, input):
        if not info.context.user.is_authenticated or info.context.user.user_type != 'ADMIN':
            raise GraphQLError("Only admin can create food types")
        
        food_type = FoodType(
            name=input.name,
            description=input.get('description', '')
        )
        food_type.save()
        return CreateFoodType(food_type=food_type)

class RecordFoodPurchase(graphene.Mutation):
    class Arguments:
        input = FoodPurchaseInput(required=True)

    purchase = graphene.Field(FoodPurchaseOutput)
    inventory = graphene.Field(FoodInventoryOutput)

    @transaction.atomic
    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.user_type != 'STOCK_MANAGER':
            raise GraphQLError("Only stock managers can record food purchases")
        
        try:
            food_type = FoodType.objects.get(pk=input.food_type_id)
            purchase = FoodPurchase(
                food_type=food_type,
                sacks_purchased=input.sacks_purchased,
                price_per_sack=input.price_per_sack,
                supplier=input.supplier,
                purchase_date=input.get('purchase_date', date.today()),
                recorded_by=user
            )
            purchase.save()
            
            return RecordFoodPurchase(
                purchase=purchase,
                inventory=FoodInventory.objects.get(food_type=food_type))
        except FoodType.DoesNotExist:
            raise GraphQLError("Food type not found")

class DistributeFood(graphene.Mutation):
    class Arguments:
        input = FoodDistributionInput(required=True)

    distribution = graphene.Field(FoodDistributionOutput)
    inventory = graphene.Field(FoodInventoryOutput)

    @transaction.atomic
    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.user_type != 'STOCK_MANAGER':
            raise GraphQLError("Only stock managers can distribute food")
        
        try:
            food_type = FoodType.objects.get(pk=input.food_type_id)
            chicken_house = ChickenHouse.objects.get(pk=input.chicken_house_id)
            worker = User.objects.filter(chicken_house=chicken_house).first()
            
            if worker.chicken_house != chicken_house:
                raise GraphQLError("Worker must be assigned to the target chicken house")
            
            inventory = FoodInventory.objects.get(food_type=food_type)
            if inventory.sacks_in_stock < input.sacks_distributed:
                raise GraphQLError("Not enough food in inventory for this distribution")
            
            distribution = FoodDistribution(
                food_type=food_type,
                chicken_house=chicken_house,
                sacks_distributed=input.sacks_distributed,
                distributed_by=user,
                received_by=worker
            )
            distribution.save()
            
            return DistributeFood(
                distribution=distribution,
                inventory=inventory
            )
        except (FoodType.DoesNotExist, ChickenHouse.DoesNotExist, UserModel.DoesNotExist):
            raise GraphQLError("Invalid food type, chicken house, or worker")

class ConfirmFoodDistribution(graphene.Mutation):
    class Arguments:
        input = FoodDistributionConfirmationInput(required=True)

    distribution = graphene.Field(FoodDistributionOutput)

    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.user_type != 'WORKER':
            raise GraphQLError("Only workers can confirm food distributions")
        
        try:
            distribution = FoodDistribution.objects.get(pk=input.distribution_id)
            if distribution.received_by != user:
                raise GraphQLError("You can only confirm distributions assigned to you")
            if distribution.worker_confirmed:
                raise GraphQLError("This distribution has already been confirmed")
            
            distribution.worker_confirmed = input.confirmed
            distribution.save()
            
            return ConfirmFoodDistribution(distribution=distribution)
        except FoodDistribution.DoesNotExist:
            raise GraphQLError("Food distribution not found")

class CreateMedicine(graphene.Mutation):
    class Arguments:
        input = MedicineInput(required=True)

    medicine = graphene.Field(MedicineOutput)

    def mutate(self, info, input):
        if not info.context.user.is_authenticated or info.context.user.user_type != 'ADMIN':
            raise GraphQLError("Only admin can create medicine records")
        
        medicine = Medicine(
            name=input.name,
            description=input.get('description', ''),
            unit_of_measure=input.unit_of_measure
        )
        medicine.save()
        return CreateMedicine(medicine=medicine)

class UpdateMedicine(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = MedicineInput(required=True)

    medicine = graphene.Field(MedicineOutput)

    def mutate(self, info, id, input):
        med = Medicine.objects.get(pk=id)
        for key, value in input.items():
            setattr(med, key, value)
        med.save()
        return UpdateMedicine(medicine=med)
    
class RecordMedicinePurchase(graphene.Mutation):
    class Arguments:
        input = MedicinePurchaseInput(required=True)

    purchase = graphene.Field(MedicinePurchaseOutput)
    inventory = graphene.Field(MedicineInventoryOutput)

    @transaction.atomic
    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.user_type != 'STOCK_MANAGER':
            raise GraphQLError("Only stock managers can record medicine purchases")
        
        try:
            medicine = Medicine.objects.get(pk=input.medicine_id)
            purchase = MedicinePurchase(
                medicine=medicine,
                quantity=input.quantity,
                price_per_unit=input.price_per_unit,
                supplier=input.supplier,
                purchase_date=input.get('purchase_date', date.today()),
                expiry_date=input.expiry_date,
                recorded_by=user
            )
            purchase.save()
            
            return RecordMedicinePurchase(
                purchase=purchase,
                inventory=MedicineInventory.objects.get(medicine=medicine)
            )
        except Medicine.DoesNotExist:
            raise GraphQLError("Medicine not found")

class DistributeMedicine(graphene.Mutation):
    class Arguments:
        input = MedicineDistributionInput(required=True)

    distribution = graphene.Field(MedicineDistributionOutput)
    inventory = graphene.Field(MedicineInventoryOutput)

    @transaction.atomic
    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.user_type != 'STOCK_MANAGER':
            raise GraphQLError("Only doctors can distribute medicine")
        
        try:
            medicine = Medicine.objects.get(pk=input.medicine_id)
            chicken_house = ChickenHouse.objects.get(pk=input.chicken_house_id)
            worker = User.objects.filter(chicken_house=chicken_house).first()
            
            if worker.chicken_house != chicken_house:
                raise GraphQLError("Worker must be assigned to the target chicken house")
            
            inventory = MedicineInventory.objects.get(medicine=medicine)
            if inventory.quantity_in_stock < float(input.quantity):
                raise GraphQLError("Not enough medicine in inventory for this distribution")
            
            distribution = MedicineDistribution(
                medicine=medicine,
                chicken_house=chicken_house,
                quantity=input.quantity,
                purpose=input.get('purpose', ''),
                distributed_by=user,
                received_by=worker
            )
            distribution.save()
            
            return DistributeMedicine(
                distribution=distribution,
                inventory=inventory
            )
        except (Medicine.DoesNotExist, ChickenHouse.DoesNotExist, UserModel.DoesNotExist):
            raise GraphQLError("Invalid medicine, chicken house, or worker")

class ConfirmMedicineDistribution(graphene.Mutation):
    class Arguments:
        input = MedicineConfirmationInput(required=True)

    distribution = graphene.Field(MedicineDistributionOutput)

    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        try:
            distribution = MedicineDistribution.objects.get(pk=input.distribution_id)
            
            # Doctor can confirm their own distributions
            if input.doctor_confirmed is not None:
                if user.user_type != 'DOCTOR':
                    raise GraphQLError("Only the distributing doctor can confirm")
                distribution.doctor_confirmed = input.doctor_confirmed
            
            # Worker can confirm their own receipts
            if input.worker_confirmed is not None:
                if user.user_type != 'WORKER' or distribution.received_by != user:
                    raise GraphQLError("Only the receiving worker can confirm")
                distribution.worker_confirmed = input.worker_confirmed
            
            distribution.save()
            return ConfirmMedicineDistribution(distribution=distribution)
        except MedicineDistribution.DoesNotExist:
            raise GraphQLError("Medicine distribution not found")

class RecordChickenDeath(graphene.Mutation):
    class Arguments:
        input = ChickenDeathRecordInput(required=True)

    record = graphene.Field(ChickenDeathRecordOutput)

    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.user_type != 'WORKER':
            raise GraphQLError("Only workers can record chicken deaths")
        
        try:
            chicken_house = user.chicken_house
            record = ChickenDeathRecord(
                chicken_house=chicken_house,
                number_dead=input.number_dead,
                possible_cause=input.get('possible_cause', ''),
                notes=input.get('notes', ''),
                recorded_by=user
            )
            record.save()
            
            # Update chicken count in the house
            chicken_house.current_chicken_count = max(
                0, chicken_house.current_chicken_count - input.number_dead
            )
            chicken_house.save()
            
            return RecordChickenDeath(record=record)
        except ChickenHouse.DoesNotExist:
            raise GraphQLError("Chicken house not found")

class ConfirmDeathRecord(graphene.Mutation):
    class Arguments:
        input = DeathRecordConfirmationInput(required=True)

    record = graphene.Field(ChickenDeathRecordOutput)

    def mutate(self, info, input):
        user = info.context.user
        if not user.is_authenticated or user.user_type != 'DOCTOR':
            raise GraphQLError("Only doctors can confirm death records")
        
        try:
            record = ChickenDeathRecord.objects.get(pk=input.record_id)
            if record.confirmed_by:
                raise GraphQLError("This death record has already been confirmed")
            
            record.confirmed_by = user
            record.doctor_notes = input.get('doctor_notes', '')
            record.save()
            
            return ConfirmDeathRecord(record=record)
        except ChickenDeathRecord.DoesNotExist:
            raise GraphQLError("Death record not found")

class Mutation(graphene.ObjectType):
    # Authentication
    login = AuthMutation.Field()
    change_password = ChangePassword.Field()
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    verify_token = graphql_jwt.Verify.Field()
    
    # User Management
    create_user = CreateUser.Field()
    
    # Chicken House Management
    create_chicken_house = CreateChickenHouse.Field()
    add_chickens_to_house = AddChickensToHouse.Field()
    update_chicken_house = UpdateChickenHouse.Field()
    
    # Egg Management
    record_egg_collection = RecordEggCollection.Field()
    confirm_egg_collection = ConfirmEggCollection.Field()
    record_egg_sale = RecordEggSale.Field()
    
    # Food Management
    create_food_type = CreateFoodType.Field()
    record_food_purchase = RecordFoodPurchase.Field()
    distribute_food = DistributeFood.Field()
    confirm_food_distribution = ConfirmFoodDistribution.Field()
    
    # Medicine Management
    create_medicine = CreateMedicine.Field()
    update_medicine = UpdateMedicine.Field()
    record_medicine_purchase = RecordMedicinePurchase.Field()
    distribute_medicine = DistributeMedicine.Field()
    confirm_medicine_distribution = ConfirmMedicineDistribution.Field()
    
    # Health Management
    record_chicken_death = RecordChickenDeath.Field()
    confirm_death_record = ConfirmDeathRecord.Field()