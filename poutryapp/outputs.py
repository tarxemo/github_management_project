from decimal import Decimal
import graphene
from graphene_django import DjangoObjectType
from django.contrib.auth import get_user_model
from .models import (
    EggDistribution, Expense, ExpenseCategory, SalaryPayment, SalesManagerInventory, 
    SystemLog, User, ChickenHouse, EggCollection, EggInventory, EggSale,
    FoodType, FoodInventory, FoodPurchase, FoodDistribution,
    Medicine, MedicineInventory, MedicinePurchase, MedicineDistribution,
    ChickenDeathRecord
)
from django.db.models import Sum
from datetime import date

UserModel = get_user_model()

# ------------------- Base Output Type -------------------
class BaseOutput(graphene.ObjectType):
    id = graphene.ID()
    is_active = graphene.Boolean()
    created_at = graphene.DateTime()
    updated_at = graphene.DateTime()
# ------------------- Output Types -------------------

class UserOutput(BaseOutput):
    phone_number = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()
    email = graphene.String()
    user_type = graphene.String()
    user_type_display = graphene.String()

    def resolve_user_type_display(self, info):
        return self.get_user_type_display()

class ChickenHouseOutput(BaseOutput):
    name = graphene.String()
    capacity = graphene.Int()
    current_chicken_count = graphene.Int()
    owner = graphene.Field(lambda: UserOutput)
    age_in_weeks = graphene.Float()
    average_weight = graphene.Float()

class EggCollectionOutput(BaseOutput):
    worker = graphene.Field(lambda: UserOutput)
    chicken_house = graphene.Field(lambda: ChickenHouseOutput)
    full_trays = graphene.Int()
    loose_eggs = graphene.Int()
    rejected_eggs = graphene.Int()
    stock_manager_confirmed = graphene.Boolean()
    stock_manager_confirmation_date = graphene.DateTime()
    notes = graphene.String()
    total_eggs = graphene.Int()

    def resolve_total_eggs(self, info):
        return (self.full_trays * 30) + self.loose_eggs

class EggInventoryOutput(BaseOutput):
    total_eggs = graphene.Int()
    rejected_eggs = graphene.Int()
    available_trays = graphene.Int()

    def resolve_available_trays(self, info):
        return self.total_eggs // 30

class EggSaleOutput(BaseOutput):
    distribution = graphene.Field(lambda: EggDistributionOutput)
    sales_manager = graphene.Field(lambda: UserOutput)
    quantity = graphene.Int()
    price_per_egg = graphene.Float()
    buyer_name = graphene.String()
    buyer_contact = graphene.String()
    confirmed = graphene.Boolean()
    sale_short = graphene.Int()
    short_reason = graphene.String()
    rejected_eggs = graphene.Int()
    reject_price = graphene.Float()
    total_amount = graphene.Float()

    def resolve_total_amount(self, info):
        return (self.quantity - self.rejected_eggs) * self.price_per_egg

class EggDistributionOutput(BaseOutput):
    stock_manager = graphene.Field(lambda: UserOutput)
    sales_manager = graphene.Field(lambda: UserOutput)
    quantity = graphene.Int()
    notes = graphene.String()
    sold_quantity = graphene.Int()
    remaining_quantity = graphene.Int()

    def resolve_sold_quantity(self, info):
        return self.sales.aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    def resolve_remaining_quantity(self, info):
        return self.quantity - self.sold_quantity

class SalesManagerInventoryOutput(BaseOutput):
    sales_manager = graphene.Field(lambda: UserOutput)
    total_eggs = graphene.Int()
    sold_eggs = graphene.Int()
    remaining_eggs = graphene.Int()

    def resolve_remaining_eggs(self, info):
        return self.total_eggs - self.sold_eggs

class FoodTypeOutput(BaseOutput):
    name = graphene.String()
    description = graphene.String()

class FoodInventoryOutput(BaseOutput):
    food_type = graphene.Field(lambda: FoodTypeOutput)
    sacks_in_stock = graphene.Int()
    total_kg = graphene.Float()

    def resolve_total_kg(self, info):
        return self.sacks_in_stock * Decimal('50')

class FoodPurchaseOutput(BaseOutput):
    food_type = graphene.Field(lambda: FoodTypeOutput)
    sacks_purchased = graphene.Int()
    price_per_sack = graphene.Float()
    supplier = graphene.String()
    recorded_by = graphene.Field(lambda: UserOutput)
    total_amount = graphene.Float()

    def resolve_total_amount(self, info):
        return self.sacks_purchased * self.price_per_sack

class FoodDistributionOutput(BaseOutput):
    food_type = graphene.Field(lambda: FoodTypeOutput)
    chicken_house = graphene.Field(lambda: ChickenHouseOutput)
    sacks_distributed = graphene.Float()
    distributed_by = graphene.Field(lambda: UserOutput)
    received_by = graphene.Field(lambda: UserOutput)
    worker_confirmed = graphene.Boolean()
    confirmation_date = graphene.DateTime()
    total_kg = graphene.Float()

    def resolve_total_kg(self, info):
        return Decimal(self.sacks_distributed) * Decimal('50')

class MedicineOutput(BaseOutput):
    name = graphene.String()
    description = graphene.String()
    unit_of_measure = graphene.String()

class MedicineInventoryOutput(BaseOutput):
    medicine = graphene.Field(lambda: MedicineOutput)
    quantity_in_stock = graphene.Float()

class MedicinePurchaseOutput(BaseOutput):
    medicine = graphene.Field(lambda: MedicineOutput)
    quantity = graphene.Float()
    price_per_unit = graphene.Float()
    supplier = graphene.String()
    expiry_date = graphene.Date()
    recorded_by = graphene.Field(lambda: UserOutput)
    total_amount = graphene.Float()
    days_to_expiry = graphene.Int()

    def resolve_total_amount(self, info):
        return self.quantity * self.price_per_unit
    
    def resolve_days_to_expiry(self, info):
        return (self.expiry_date - date.today()).days

class MedicineDistributionOutput(BaseOutput):
    medicine = graphene.Field(lambda: MedicineOutput)
    chicken_house = graphene.Field(lambda: ChickenHouseOutput)
    quantity = graphene.Float()
    distributed_by = graphene.Field(lambda: UserOutput)
    received_by = graphene.Field(lambda: UserOutput)
    doctor_confirmed = graphene.Boolean()
    worker_confirmed = graphene.Boolean()
    purpose = graphene.String()

class ChickenDeathRecordOutput(BaseOutput):
    chicken_house = graphene.Field(lambda: ChickenHouseOutput)
    number_dead = graphene.Int()
    recorded_by = graphene.Field(lambda: UserOutput)
    confirmed_by = graphene.Field(lambda: UserOutput)
    notes = graphene.String()
    doctor_notes = graphene.String()
    possible_cause = graphene.String()

class ExpenseCategoryOutput(BaseOutput):
    name = graphene.String()
    description = graphene.String()

class ExpenseOutput(BaseOutput):
    category = graphene.Field(lambda: ExpenseCategoryOutput)
    description = graphene.String()
    payment_method = graphene.String()
    unit_cost = graphene.Float()       # changed here
    quantity = graphene.Float()        # changed here
    total_cost = graphene.Float()      # changed here
    recorded_by = graphene.Field(lambda: UserOutput)
    receipt_number = graphene.String()
    notes = graphene.String()


class SalaryPaymentOutput(BaseOutput):
    worker = graphene.Field(lambda: UserOutput)
    amount = graphene.Float()
    payment_method = graphene.String()
    period_start = graphene.Date()
    period_end = graphene.Date()
    recorded_by = graphene.Field(lambda: UserOutput)
    notes = graphene.String()

class SystemLogOutput(BaseOutput):
    user = graphene.Field(lambda: UserOutput)
    action = graphene.String()
    model_name = graphene.String()
    object_id = graphene.String()
    timestamp = graphene.DateTime()
    ip_address = graphene.String()
    user_agent = graphene.String()
    before_state = graphene.JSONString()
    after_state = graphene.JSONString()
    changes = graphene.JSONString()

    def resolve_before_state(self, info):
        return self.before_state

    def resolve_after_state(self, info):
        return self.after_state

    def resolve_changes(self, info):
        return self.changes

# ------------------- Custom Business-Focused Types -------------------

class DailyEggReportOutput(graphene.ObjectType):
    date = graphene.Date()
    total_eggs = graphene.Int()
    total_trays = graphene.Int()
    total_rejected = graphene.Int()
    collections = graphene.List(lambda: EggCollectionOutput)
    
    def resolve_total_trays(self, info):
        return self.total_eggs // 30

class ChickenHousePerformanceOutput(graphene.ObjectType):
    chicken_house = graphene.Field(lambda: ChickenHouseOutput)
    total_eggs = graphene.Int()
    avg_eggs_per_day = graphene.Float()
    mortality_rate = graphene.Float()
    food_consumption = graphene.Float()

class InventorySummaryOutput(graphene.ObjectType):
    total_eggs = graphene.Int()
    available_trays = graphene.Int()
    food_inventory = graphene.List(lambda: FoodInventoryOutput)
    medicine_inventory = graphene.List(lambda: MedicineInventoryOutput)
    total_users = graphene.Int()
    
    def resolve_total_users(self, info):
        return User.objects.exclude(is_superuser=True).count()
    
    def resolve_available_trays(self, info):
        return self.total_eggs // 30

class AlertOutput(graphene.ObjectType):
    type = graphene.String()
    title = graphene.String()
    message = graphene.String()