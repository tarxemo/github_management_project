# import graphene
# from graphene import Mutation, Field
# from graphql import GraphQLError
# from django.db import transaction
# from .models import *
# from .inputs import *
# from .outputs import *
# from django.contrib.auth import get_user_model
# from django.contrib.auth.hashers import make_password

# User = get_user_model()

# class CreateUser(Mutation):
#     class Arguments:
#         input = UserInput(required=True)

#     user = Field(UserOutput)
    
#     @classmethod
#     def mutate(cls, root, info, input):
#         try:
#             with transaction.atomic():
#                 # Hash password before saving
#                 input['password'] = make_password(input['password'])
#                 user = User.objects.create(**input)
#                 return CreateUser(user=user)
#         except Exception as e:
#             raise GraphQLError(f"Error creating user: {str(e)}")

# class UpdateUser(Mutation):
#     class Arguments:
#         id = ID(required=True)
#         input = UserInput(required=True)

#     user = Field(UserOutput)
    
#     @classmethod
#     def mutate(cls, root, info, id, input):
#         try:
#             user = User.objects.get(pk=id)
#             for key, value in input.items():
#                 if key == 'password' and value:
#                     user.password = make_password(value)
#                 else:
#                     setattr(user, key, value)
#             user.save()
#             return UpdateUser(user=user)
#         except User.DoesNotExist:
#             raise GraphQLError("User not found")
#         except Exception as e:
#             raise GraphQLError(f"Error updating user: {str(e)}")

# class CreateChickenHouse(Mutation):
#     class Arguments:
#         input = ChickenHouseInput(required=True)

#     chicken_house = Field(ChickenHouseOutput)
    
#     @classmethod
#     def mutate(cls, root, info, input):
#         try:
#             worker_id = input.pop('worker_id', None)
#             chicken_house = ChickenHouse.objects.create(**input)
#             if worker_id:
#                 worker = User.objects.get(pk=worker_id, user_type='WORKER')
#                 chicken_house.worker = worker
#                 chicken_house.save()
#             return CreateChickenHouse(chicken_house=chicken_house)
#         except Exception as e:
#             raise GraphQLError(f"Error creating chicken house: {str(e)}")

# class RecordEggCollection(Mutation):
#     class Arguments:
#         input = EggCollectionInput(required=True)

#     egg_collection = Field(EggCollectionOutput)
#     # inventory = Field(InventoryOutput)
    
#     @classmethod
#     def mutate(cls, root, info, input):
#         try:
#             with transaction.atomic():
#                 chicken_house_id = input.pop('chicken_house_id')
#                 collected_by_id = input.pop('collected_by_id', None)
                
#                 chicken_house = ChickenHouse.objects.get(pk=chicken_house_id)
#                 collected_by = User.objects.get(pk=collected_by_id) if collected_by_id else None
                
#                 egg_collection = EggCollection.objects.create(
#                     chicken_house=chicken_house,
#                     collected_by=collected_by,
#                     **input
#                 )
                
#                 # Update inventory
#                 inventory, _ = Inventory.objects.get_or_create(pk=1)
#                 inventory.egg_count += egg_collection.total_eggs
#                 inventory.save()
                
#                 return RecordEggCollection(egg_collection=egg_collection, inventory=inventory)
#         except Exception as e:
#             raise GraphQLError(f"Error recording egg collection: {str(e)}")

# class RecordVaccination(Mutation):
#     class Arguments:
#         input = VaccinationRecordInput(required=True)

#     vaccination = Field(VaccinationRecordOutput)
    
#     @classmethod
#     def mutate(cls, root, info, input):
#         try:
#             with transaction.atomic():
#                 chicken_house_id = input.pop('chicken_house_id')
#                 vaccine_id = input.pop('vaccine_id')
#                 administered_by_id = input.pop('administered_by_id', None)
                
#                 chicken_house = ChickenHouse.objects.get(pk=chicken_house_id)
#                 vaccine = Vaccine.objects.get(pk=vaccine_id)
#                 administered_by = User.objects.get(pk=administered_by_id) if administered_by_id else None
                
#                 vaccination = VaccinationRecord.objects.create(
#                     chicken_house=chicken_house,
#                     vaccine=vaccine,
#                     administered_by=administered_by,
#                     **input
#                 )
                
#                 return RecordVaccination(vaccination=vaccination)
#         except Exception as e:
#             raise GraphQLError(f"Error recording vaccination: {str(e)}")

# class ProcessSale(Mutation):
#     class Arguments:
#         input = SaleInput(required=True)
#         items = List(SaleItemInput, required=True)

#     sale = Field(SaleOutput)
#     inventory = Field(InventoryOutput)
    
#     @classmethod
#     def mutate(cls, root, info, input, items):
#         try:
#             with transaction.atomic():
#                 # Create the sale
#                 customer_id = input.pop('customer_id', None)
#                 sales_manager_id = input.pop('sales_manager_id')
                
#                 customer = User.objects.get(pk=customer_id) if customer_id else None
#                 sales_manager = User.objects.get(pk=sales_manager_id, user_type='SALES_MANAGER')
                
#                 sale = Sale.objects.create(
#                     customer=customer,
#                     sales_manager=sales_manager,
#                     **input
#                 )
                
#                 # Process sale items
#                 inventory, _ = Inventory.objects.get_or_create(pk=1)
                
#                 for item in items:
#                     sale_id = item.pop('sale_id', None)
#                     chicken_id = item.pop('chicken_id', None)
                    
#                     if sale.sale_type == 'EGG':
#                         eggs_sold = (item['egg_trays'] * 30) + item['egg_singles']
#                         if eggs_sold > inventory.egg_count:
#                             raise GraphQLError("Not enough eggs in inventory")
#                         inventory.egg_count -= eggs_sold
#                     elif sale.sale_type == 'CHICKEN' and chicken_id:
#                         chicken = Chicken.objects.get(pk=chicken_id, is_alive=True)
#                         chicken.is_alive = False
#                         chicken.date_of_death = sale.sale_date.date()
#                         chicken.save()
                        
#                         # Update chicken house count
#                         chicken_house = chicken.chicken_house
#                         chicken_house.current_chicken_count -= 1
#                         chicken_house.save()
                    
#                     SaleItem.objects.create(sale=sale, **item)
                
#                 inventory.save()
#                 return ProcessSale(sale=sale, inventory=inventory)
#         except Exception as e:
#             raise GraphQLError(f"Error processing sale: {str(e)}")

# class RecordFoodPurchase(Mutation):
#     class Arguments:
#         input = FoodPurchaseInput(required=True)

#     food_purchase = Field(FoodPurchaseOutput)
    
#     @classmethod
#     def mutate(cls, root, info, input):
#         try:
#             with transaction.atomic():
#                 food_id = input.pop('food_id')
#                 food = Food.objects.get(pk=food_id)
                
#                 food_purchase = FoodPurchase.objects.create(
#                     food=food,
#                     **input
#                 )
                
#                 return RecordFoodPurchase(food_purchase=food_purchase)
#         except Exception as e:
#             raise GraphQLError(f"Error recording food purchase: {str(e)}")

# class DistributeFood(Mutation):
#     class Arguments:
#         input = FoodDistributionInput(required=True)

#     distribution = Field(FoodDistributionOutput)
    
#     @classmethod
#     def mutate(cls, root, info, input):
#         try:
#             with transaction.atomic():
#                 chicken_house_id = input.pop('chicken_house_id')
#                 food_id = input.pop('food_id')
#                 distributed_by_id = input.pop('distributed_by_id', None)
                
#                 chicken_house = ChickenHouse.objects.get(pk=chicken_house_id)
#                 food = Food.objects.get(pk=food_id)
#                 distributed_by = User.objects.get(pk=distributed_by_id) if distributed_by_id else None
                
#                 distribution = FoodDistribution.objects.create(
#                     chicken_house=chicken_house,
#                     food=food,
#                     distributed_by=distributed_by,
#                     **input
#                 )
                
#                 return DistributeFood(distribution=distribution)
#         except Exception as e:
#             raise GraphQLError(f"Error distributing food: {str(e)}")

# class RecordExpense(Mutation):
#     class Arguments:
#         input = ExpenseInput(required=True)

#     expense = Field(ExpenseOutput)
    
#     @classmethod
#     def mutate(cls, root, info, input):
#         try:
#             with transaction.atomic():
#                 recorded_by_id = input.pop('recorded_by_id', None)
#                 recorded_by = User.objects.get(pk=recorded_by_id) if recorded_by_id else None
                
#                 expense = Expense.objects.create(
#                     recorded_by=recorded_by,
#                     **input
#                 )
                
#                 return RecordExpense(expense=expense)
#         except Exception as e:
#             raise GraphQLError(f"Error recording expense: {str(e)}")

# class RecordHealthReport(Mutation):
#     class Arguments:
#         input = HealthReportInput(required=True)

#     health_report = Field(HealthReportOutput)
    
#     @classmethod
#     def mutate(cls, root, info, input):
#         try:
#             with transaction.atomic():
#                 chicken_house_id = input.pop('chicken_house_id')
#                 reported_by_id = input.pop('reported_by_id', None)
                
#                 chicken_house = ChickenHouse.objects.get(pk=chicken_house_id)
#                 reported_by = User.objects.get(pk=reported_by_id, user_type='DOCTOR') if reported_by_id else None
                
#                 health_report = HealthReport.objects.create(
#                     chicken_house=chicken_house,
#                     reported_by=reported_by,
#                     **input
#                 )
                
#                 return RecordHealthReport(health_report=health_report)
#         except Exception as e:
#             raise GraphQLError(f"Error recording health report: {str(e)}")

# class AddChickensToHouse(Mutation):
#     class Arguments:
#         chicken_house_id = ID(required=True)
#         count = Int(required=True)
#         chicken_type = String(required=True)

#     chicken_house = Field(ChickenHouseOutput)
    
#     @classmethod
#     def mutate(cls, root, info, chicken_house_id, count, chicken_type):
#         try:
#             with transaction.atomic():
#                 chicken_house = ChickenHouse.objects.get(pk=chicken_house_id)
                
#                 if chicken_house.current_chicken_count + count > chicken_house.capacity:
#                     raise GraphQLError("Adding these chickens would exceed house capacity")
                
#                 # Create chickens in bulk
#                 chickens = [
#                     Chicken(
#                         chicken_house=chicken_house,
#                         chicken_type=chicken_type,
#                         gender='UNKNOWN'  # Default, can be updated later
#                     )
#                     for _ in range(count)
#                 ]
#                 Chicken.objects.bulk_create(chickens)
                
#                 # Update house count
#                 chicken_house.current_chicken_count += count
#                 chicken_house.save()
                
#                 return AddChickensToHouse(chicken_house=chicken_house)
#         except Exception as e:
#             raise GraphQLError(f"Error adding chickens to house: {str(e)}")

# class RecordChickenDeath(Mutation):
#     class Arguments:
#         chicken_id = ID(required=True)
#         cause_of_death = String(required=True)
#         date_of_death = Date()

#     chicken = Field(ChickenOutput)
#     chicken_house = Field(ChickenHouseOutput)
    
#     @classmethod
#     def mutate(cls, root, info, chicken_id, cause_of_death, date_of_death=None):
#         try:
#             with transaction.atomic():
#                 chicken = Chicken.objects.get(pk=chicken_id, is_alive=True)
#                 chicken.is_alive = False
#                 chicken.cause_of_death = cause_of_death
#                 chicken.date_of_death = date_of_death or timezone.now().date()
#                 chicken.save()
                
#                 # Update chicken house count
#                 chicken_house = chicken.chicken_house
#                 chicken_house.current_chicken_count -= 1
#                 chicken_house.save()
                
#                 return RecordChickenDeath(chicken=chicken, chicken_house=chicken_house)
#         except Chicken.DoesNotExist:
#             raise GraphQLError("Chicken not found or already dead")
#         except Exception as e:
#             raise GraphQLError(f"Error recording chicken death: {str(e)}")

# class UpdateInventory(Mutation):
#     class Arguments:
#         input = InventoryUpdateInput(required=True)

#     inventory = Field(InventoryOutput)
    
#     @classmethod
#     def mutate(cls, root, info, input):
#         try:
#             inventory, _ = Inventory.objects.get_or_create(pk=1)
#             inventory.egg_count = input['egg_count']
#             inventory.save()
#             return UpdateInventory(inventory=inventory)
#         except Exception as e:
#             raise GraphQLError(f"Error updating inventory: {str(e)}")

# class Mutation(graphene.ObjectType):
#     create_user = CreateUser.Field()
#     update_user = UpdateUser.Field()
#     create_chicken_house = CreateChickenHouse.Field()
#     record_egg_collection = RecordEggCollection.Field()
#     record_vaccination = RecordVaccination.Field()
#     process_sale = ProcessSale.Field()
#     record_food_purchase = RecordFoodPurchase.Field()
#     distribute_food = DistributeFood.Field()
#     record_expense = RecordExpense.Field()
#     record_health_report = RecordHealthReport.Field()
#     add_chickens_to_house = AddChickensToHouse.Field()
#     record_chicken_death = RecordChickenDeath.Field()
#     update_inventory = UpdateInventory.Field()
