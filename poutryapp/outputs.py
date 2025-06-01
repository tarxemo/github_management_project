import graphene
from graphene import ObjectType, ID, String, Int, Float, Boolean, Date, DateTime, List, Field
from graphene_django.types import DjangoObjectType
from .models import (
    User, ChickenHouse, Chicken, Vaccine, VaccinationRecord,
    EggCollection, Food, FoodPurchase, FoodDistribution,
    Inventory, Sale, SaleItem, Expense, HealthReport
)

class UserOutput(ObjectType):
    id = ID()
    username = String()
    email = String()
    user_type = String()
    phone_number = String()
    address = String()
    date_joined = DateTime()
    last_login = DateTime()
    
    def resolve_user_type(self, info):
        return self.get_user_type_display()

class ChickenHouseOutput(ObjectType):
    id = ID()
    name = String()
    house_type = String()
    capacity = Int()
    current_chicken_count = Int()
    worker = Field(lambda: UserOutput)
    created_at = DateTime()
    last_cleaned = DateTime()
    notes = String()
    
    def resolve_house_type(self, info):
        return self.get_house_type_display()

class ChickenOutput(ObjectType):
    id = ID()
    chicken_house = Field(lambda: ChickenHouseOutput)
    chicken_type = String()
    gender = String()
    date_added = Date()
    date_of_birth = Date()
    is_alive = Boolean()
    date_of_death = Date()
    cause_of_death = String()
    notes = String()
    
    def resolve_chicken_type(self, info):
        return self.get_chicken_type_display()
    
    def resolve_gender(self, info):
        return self.get_gender_display()

class VaccineOutput(ObjectType):
    id = ID()
    name = String()
    description = String()
    recommended_age_days = Int()

class VaccinationRecordOutput(ObjectType):
    id = ID()
    chicken_house = Field(lambda: ChickenHouseOutput)
    vaccine = Field(lambda: VaccineOutput)
    date_administered = Date()
    administered_by = Field(lambda: UserOutput)
    notes = String()

class EggCollectionOutput(ObjectType):
    id = ID()
    chicken_house = Field(lambda: ChickenHouseOutput)
    collection_date = Date()
    collected_by = Field(lambda: UserOutput)
    total_eggs = Int()
    broken_eggs = Int()
    full_trays = Int()
    remaining_eggs = Int()
    notes = String()
    
    def resolve_full_trays(self, info):
        return self.total_eggs // 30
    
    def resolve_remaining_eggs(self, info):
        return self.total_eggs % 30

class FoodOutput(ObjectType):
    id = ID()
    name = String()
    description = String()
    unit = String()

class FoodPurchaseOutput(ObjectType):
    id = ID()
    food = Field(lambda: FoodOutput)
    quantity = Float()
    unit_price = Float()
    purchase_date = Date()
    supplier = String()
    receipt_number = String()
    notes = String()
    total_cost = Float()
    
    def resolve_total_cost(self, info):
        return self.quantity * self.unit_price

class FoodDistributionOutput(ObjectType):
    id = ID()
    chicken_house = Field(lambda: ChickenHouseOutput)
    food = Field(lambda: FoodOutput)
    quantity = Float()
    distribution_date = DateTime()
    distributed_by = Field(lambda: UserOutput)
    notes = String()

class InventoryOutput(ObjectType):
    id = ID()
    egg_count = Int()
    last_updated = DateTime()

class SaleOutput(ObjectType):
    id = ID()
    sale_type = String()
    customer = Field(lambda: UserOutput)
    sales_manager = Field(lambda: UserOutput)
    sale_date = DateTime()
    total_amount = Float()
    payment_received = Boolean()
    payment_method = String()
    notes = String()
    items = List(lambda: SaleItemOutput)
    
    def resolve_sale_type(self, info):
        return self.get_sale_type_display()
    
    def resolve_items(self, info):
        return self.items.all()

class SaleItemOutput(ObjectType):
    id = ID()
    sale = Field(lambda: SaleOutput)
    egg_trays = Int()
    egg_singles = Int()
    egg_price_per_tray = Float()
    chicken = Field(lambda: ChickenOutput)
    chicken_price = Float()
    item_description = String()
    quantity = Float()
    unit_price = Float()
    total_price = Float()
    
    def resolve_total_price(self, info):
        if self.sale.sale_type == 'EGG':
            return (self.egg_trays * self.egg_price_per_tray) + \
                   (self.egg_singles * (self.egg_price_per_tray / 30))
        elif self.sale.sale_type == 'CHICKEN' and self.chicken:
            return self.chicken_price
        else:
            return self.quantity * self.unit_price

class ExpenseOutput(ObjectType):
    id = ID()
    expense_type = String()
    amount = Float()
    date = Date()
    description = String()
    recorded_by = Field(lambda: UserOutput)
    
    def resolve_expense_type(self, info):
        return self.get_expense_type_display()

class HealthReportOutput(ObjectType):
    id = ID()
    chicken_house = Field(lambda: ChickenHouseOutput)
    report_date = Date()
    reported_by = Field(lambda: UserOutput)
    healthy_count = Int()
    sick_count = Int()
    symptoms = String()
    treatment = String()
    notes = String()

class BusinessMetricsOutput(ObjectType):
    total_eggs_collected = Int()
    total_eggs_sold = Int()
    total_chickens_sold = Int()
    total_revenue = Float()
    total_expenses = Float()
    net_profit = Float()
    food_costs = Float()
    health_costs = Float()
    operational_costs = Float()