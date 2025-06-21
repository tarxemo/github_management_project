from decimal import Decimal
import graphene
from graphene_django import DjangoObjectType
from django.contrib.auth import get_user_model
from .models import (
    User, ChickenHouse, EggCollection, EggInventory, EggSale,
    FoodType, FoodInventory, FoodPurchase, FoodDistribution,
    Medicine, MedicineInventory, MedicinePurchase, MedicineDistribution,
    ChickenDeathRecord
)
from datetime import date

UserModel = get_user_model()
# ------------------- Output Types -------------------

class UserOutput(DjangoObjectType):
    class Meta:
        model = UserModel
        only_fields = (
            'id', 'phone_number', 'first_name', 'last_name', 
            'user_type'
        )
    
    user_type_display = graphene.String()
    
    def resolve_user_type_display(self, info):
        return self.get_user_type_display()
    

class ChickenHouseOutput(DjangoObjectType):
    class Meta:
        model = ChickenHouse
        fields = '__all__'
    

class EggCollectionOutput(DjangoObjectType):
    class Meta:
        model = EggCollection
        fields = '__all__'
    
    total_eggs = graphene.Int()
    chicken_house = graphene.Field(lambda: ChickenHouseOutput)
    worker = graphene.Field(lambda: UserOutput)
    
    def resolve_total_eggs(self, info):
        return (self.full_trays * 30) + self.loose_eggs

class EggInventoryOutput(DjangoObjectType):
    class Meta:
        model = EggInventory
        fields = '__all__'
    
    available_trays = graphene.Int()
    
    def resolve_available_trays(self, info):
        return self.total_eggs // 30

class EggSaleOutput(DjangoObjectType):
    class Meta:
        model = EggSale
        fields = '__all__'
    
    total_amount = graphene.Decimal()
    recorded_by = graphene.Field(lambda: UserOutput)
    
    def resolve_total_amount(self, info):
        return self.quantity * Decimal(f'{self.price_per_egg}')

class FoodTypeOutput(DjangoObjectType):
    class Meta:
        model = FoodType
        fields = '__all__'

class FoodInventoryOutput(DjangoObjectType):
    class Meta:
        model = FoodInventory
        fields = '__all__'
    
    food_type = graphene.Field(lambda: FoodTypeOutput)
    total_kg = graphene.Decimal()
    
    def resolve_total_kg(self, info):
        return self.sacks_in_stock * Decimal('50')

class FoodPurchaseOutput(DjangoObjectType):
    class Meta:
        model = FoodPurchase
        fields = '__all__'
    
    food_type = graphene.Field(lambda: FoodTypeOutput)
    recorded_by = graphene.Field(lambda: UserOutput)
    total_amount = graphene.Decimal()
    
    def resolve_total_amount(self, info):
        return self.sacks_purchased * Decimal(f'{self.price_per_sack}')

class FoodDistributionOutput(DjangoObjectType):
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

class MedicineOutput(DjangoObjectType):
    class Meta:
        model = Medicine
        fields = '__all__'

class MedicineInventoryOutput(DjangoObjectType):
    class Meta:
        model = MedicineInventory
        fields = '__all__'
    
    medicine = graphene.Field(lambda: MedicineOutput)

class MedicinePurchaseOutput(DjangoObjectType):
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

class MedicineDistributionOutput(DjangoObjectType):
    class Meta:
        model = MedicineDistribution
        fields = '__all__'
    
    medicine = graphene.Field(lambda: MedicineOutput)
    chicken_house = graphene.Field(lambda: ChickenHouseOutput)
    distributed_by = graphene.Field(lambda: UserOutput)
    received_by = graphene.Field(lambda: UserOutput)

class ChickenDeathRecordOutput(DjangoObjectType):
    class Meta:
        model = ChickenDeathRecord
        fields = '__all__'
    
    chicken_house = graphene.Field(lambda: ChickenHouseOutput)
    recorded_by = graphene.Field(lambda: UserOutput)
    confirmed_by = graphene.Field(lambda: UserOutput)
    
    def resolve_confirmed_by(self, info):
        return self.confirmed_by  # ✅ No .from_orm needed

    def resolve_recorded_by(self, info):
        return self.recorded_by  # ✅ Same here

    def resolve_chicken_house(self, info):
        return self.chicken_house  # ✅ And here


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
    
    def resolve_avg_eggs_per_day(self, info):
        # Business logic to calculate average eggs per day
        pass
    
    def resolve_mortality_rate(self, info):
        # Business logic to calculate mortality rate
        pass
    
    def resolve_food_consumption(self, info):
        # Business logic to calculate food consumption
        pass

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

class AlertType(graphene.ObjectType):
    type = graphene.String()
    title = graphene.String()
    message = graphene.String()