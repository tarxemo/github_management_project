from decimal import Decimal
import graphene
from graphene_django import DjangoObjectType
from django.contrib.auth import get_user_model
from .models import (
    Expense, ExpenseCategory, SalaryPayment, SystemLog, User, ChickenHouse, EggCollection, EggInventory, EggSale,
    FoodType, FoodInventory, FoodPurchase, FoodDistribution,
    Medicine, MedicineInventory, MedicinePurchase, MedicineDistribution,
    ChickenDeathRecord, BaseModel
)
from datetime import date
from graphene import relay

UserModel = get_user_model()

# ------------------- Base Output Type -------------------
class BaseOutput(DjangoObjectType):
    class Meta:
        abstract = True
    
    is_active = graphene.Boolean()
    created_at = graphene.DateTime()
    updated_at = graphene.DateTime()

# ------------------- Output Types -------------------

class UserOutput(DjangoObjectType):
    class Meta:
        model = UserModel
        only_fields = (
            'id', 'phone_number', 'first_name', 'last_name', 
            'user_type', 'is_active', 'created_at', 'updated_at'
        )
    
    user_type_display = graphene.String()
    
    def resolve_user_type_display(self, info):
        return self.get_user_type_display()

class ChickenHouseOutput(BaseOutput):
    class Meta:
        model = ChickenHouse
        fields = '__all__'

class EggCollectionOutput(BaseOutput):
    class Meta:
        model = EggCollection
        fields = '__all__'
    
    total_eggs = graphene.Int()
    chicken_house = graphene.Field(lambda: ChickenHouseOutput)
    worker = graphene.Field(lambda: UserOutput)
    
    def resolve_total_eggs(self, info):
        return (self.full_trays * 30) + self.loose_eggs

class EggInventoryOutput(BaseOutput):
    class Meta:
        model = EggInventory
        fields = '__all__'
    
    available_trays = graphene.Int()
    
    def resolve_available_trays(self, info):
        return self.total_eggs // 30

class EggSaleOutput(BaseOutput):
    class Meta:
        model = EggSale
        fields = '__all__'
    
    total_amount = graphene.Decimal()
    recorded_by = graphene.Field(lambda: UserOutput)
    
    def resolve_total_amount(self, info):
        return self.quantity * Decimal(f'{self.price_per_egg}')

class FoodTypeOutput(BaseOutput):
    class Meta:
        model = FoodType
        fields = '__all__'

class FoodInventoryOutput(BaseOutput):
    class Meta:
        model = FoodInventory
        fields = '__all__'
    
    food_type = graphene.Field(lambda: FoodTypeOutput)
    total_kg = graphene.Decimal()
    
    def resolve_total_kg(self, info):
        return self.sacks_in_stock * Decimal('50')

class FoodPurchaseOutput(BaseOutput):
    class Meta:
        model = FoodPurchase
        fields = '__all__'
    
    food_type = graphene.Field(lambda: FoodTypeOutput)
    recorded_by = graphene.Field(lambda: UserOutput)
    total_amount = graphene.Decimal()
    
    def resolve_total_amount(self, info):
        return self.sacks_purchased * Decimal(f'{self.price_per_sack}')

class FoodDistributionOutput(BaseOutput):
    class Meta:
        model = FoodDistribution
        fields = '__all__'
    
    food_type = graphene.Field(lambda: FoodTypeOutput)
    chicken_house = graphene.Field(lambda: ChickenHouseOutput)
    distributed_by = graphene.Field(lambda: UserOutput)
    received_by = graphene.Field(lambda: UserOutput)
    total_kg = graphene.Decimal()
    
    def resolve_total_kg(self, info):
        return self.sacks_distributed * Decimal('50')

class MedicineOutput(BaseOutput):
    class Meta:
        model = Medicine
        fields = '__all__'

class MedicineInventoryOutput(BaseOutput):
    class Meta:
        model = MedicineInventory
        fields = '__all__'
    
    medicine = graphene.Field(lambda: MedicineOutput)

class MedicinePurchaseOutput(BaseOutput):
    class Meta:
        model = MedicinePurchase
        fields = '__all__'
    
    medicine = graphene.Field(lambda: MedicineOutput)
    recorded_by = graphene.Field(lambda: UserOutput)
    total_amount = graphene.Decimal()
    days_to_expiry = graphene.Int()
    
    def resolve_total_amount(self, info):
        return Decimal(self.quantity) * Decimal(self.price_per_unit)
    
    def resolve_days_to_expiry(self, info):
        return (self.expiry_date - date.today()).days

class MedicineDistributionOutput(BaseOutput):
    class Meta:
        model = MedicineDistribution
        fields = '__all__'
    
    medicine = graphene.Field(lambda: MedicineOutput)
    chicken_house = graphene.Field(lambda: ChickenHouseOutput)
    distributed_by = graphene.Field(lambda: UserOutput)
    received_by = graphene.Field(lambda: UserOutput)

class ChickenDeathRecordOutput(BaseOutput):
    class Meta:
        model = ChickenDeathRecord
        fields = '__all__'
    
    chicken_house = graphene.Field(lambda: ChickenHouseOutput)
    recorded_by = graphene.Field(lambda: UserOutput)
    confirmed_by = graphene.Field(lambda: UserOutput)

class ExpenseCategoryOutput(BaseOutput):
    class Meta:
        model = ExpenseCategory
        fields = '__all__'
        # interfaces = (relay.Node,)
        filter_fields = {
            'name': ['exact', 'icontains'],
        }

class ExpenseOutput(BaseOutput):
    class Meta:
        model = Expense
        fields = '__all__'
        # interfaces = (relay.Node,)
        filter_fields = {
            'category__name': ['exact', 'icontains'],
            'created_at': ['exact', 'gte', 'lte'],
            'total_cost': ['gte', 'lte'],
            'payment_method': ['exact'],
        }

class SalaryPaymentOutput(BaseOutput):
    class Meta:
        model = SalaryPayment
        fields = '__all__'
        # interfaces = (relay.Node,)
        filter_fields = {
            'worker__id': ['exact'],
            'created_at': ['exact', 'gte', 'lte'],
            'amount': ['gte', 'lte'],
        }

class SystemLogOutput(DjangoObjectType):
    class Meta:
        model = SystemLog
        fields = '__all__'
        # interfaces = (relay.Node,)

    before_state = graphene.JSONString()
    after_state = graphene.JSONString()
    changes = graphene.JSONString()
    user = graphene.Field(lambda: UserOutput)

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
    food_consumption = graphene.Decimal()

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