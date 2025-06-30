import graphene
from django.contrib.auth import get_user_model

UserModel = get_user_model()

# ------------------- Input Types -------------------

class UserInput(graphene.InputObjectType):
    phone_number = graphene.String(required=True)
    password = graphene.String(required=True)
    first_name = graphene.String()
    last_name = graphene.String()
    user_type = graphene.String(required=True)
    # chicken_house_id = graphene.ID()

class UpdateUserInput(graphene.InputObjectType):
    phone_number = graphene.String(required=True)
    # password = graphene.String(required=True)
    first_name = graphene.String()
    last_name = graphene.String()
    user_type = graphene.String(required=True)
    # chicken_house_id = graphene.ID()
    


class ChangePasswordInput(graphene.InputObjectType):
    old_password = graphene.String(required=True)
    new_password = graphene.String(required=True)
    
class AddChickensInput(graphene.InputObjectType):
    chicken_house_id = graphene.ID(required=True)
    number_of_chickens = graphene.Int(required=True)
    
class ChickenHouseInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    capacity = graphene.Int(required=True)
    is_active = graphene.Boolean()
    worker_id = graphene.ID(required=True)
    age_in_weeks = graphene.Int()
    average_weight = graphene.Decimal()
    
class EggCollectionInput(graphene.InputObjectType):
    chicken_house_id = graphene.ID(required=True)
    full_trays = graphene.Int(required=True)
    loose_eggs = graphene.Int(default_value=0)
    rejected_eggs = graphene.Int(default_value=0)
    notes = graphene.String()

class EggCollectionConfirmationInput(graphene.InputObjectType):
    collection_id = graphene.ID(required=True)
    confirmed = graphene.Boolean(required=True)

class EggSaleInput(graphene.InputObjectType):
    id = graphene.ID()
    quantity = graphene.Int()
    price_per_egg = graphene.Decimal()
    buyer_name = graphene.String()
    buyer_contact = graphene.String()
    remained_eggs = graphene.Int()
    rejected_eggs = graphene.Int()
    confirm_received = graphene.Boolean()
    confirm_sales = graphene.Boolean()

    
class FoodTypeInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    description = graphene.String()

class FoodPurchaseInput(graphene.InputObjectType):
    food_type_id = graphene.ID(required=True)
    sacks_purchased = graphene.Int(required=True)
    price_per_sack = graphene.Decimal(required=True)
    supplier = graphene.String(required=True)
    created_at = graphene.Date()

class FoodDistributionInput(graphene.InputObjectType):
    food_type_id = graphene.ID(required=True)
    chicken_house_id = graphene.ID(required=True)
    sacks_distributed = graphene.Decimal(required=True)

class FoodDistributionConfirmationInput(graphene.InputObjectType):
    distribution_id = graphene.ID(required=True)
    confirmed = graphene.Boolean(required=True)

class MedicineInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    description = graphene.String()
    unit_of_measure = graphene.String(required=True)

class MedicinePurchaseInput(graphene.InputObjectType):
    medicine_id = graphene.ID(required=True)
    quantity = graphene.Decimal(required=True)
    price_per_unit = graphene.Decimal(required=True)
    supplier = graphene.String(required=True)
    created_at = graphene.Date()
    expiry_date = graphene.Date(required=True)

class MedicineDistributionInput(graphene.InputObjectType):
    medicine_id = graphene.ID(required=True)
    chicken_house_id = graphene.ID(required=True)
    quantity = graphene.Decimal(required=True)
    purpose = graphene.String()

class MedicineConfirmationInput(graphene.InputObjectType):
    distribution_id = graphene.ID(required=True)
    doctor_confirmed = graphene.Boolean()
    worker_confirmed = graphene.Boolean()

class ChickenDeathRecordInput(graphene.InputObjectType):
    number_dead = graphene.Int(required=True)
    possible_cause = graphene.String()
    notes = graphene.String()
    chicken_house_id = graphene.ID()
    
class DeathRecordConfirmationInput(graphene.InputObjectType):
    record_id = graphene.ID(required=True)
    confirmed = graphene.Boolean(required=True)
    doctor_notes = graphene.String()

class ExpenseCategoryInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    description = graphene.String()

class ExpenseInput(graphene.InputObjectType):
    category_id = graphene.String(required=True)
    date = graphene.Date()
    description = graphene.String(required=True)
    payment_method = graphene.String()
    unit_cost = graphene.Decimal(required=True)
    quantity = graphene.Decimal()
    receipt_number = graphene.String()
    notes = graphene.String()

class SalaryPaymentInput(graphene.InputObjectType):
    worker_id = graphene.ID(required=True)
    amount = graphene.Decimal(required=True)
    created_at = graphene.Date()
    payment_method = graphene.String()
    period_start = graphene.Date(required=True)
    period_end = graphene.Date(required=True)
    notes = graphene.String()