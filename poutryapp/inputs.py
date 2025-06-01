import graphene
from graphene import InputObjectType, ID, String, Int, Float, Boolean, Date, DateTime, List

class UserInput(InputObjectType):
    username = String(required=True)
    email = String(required=True)
    password = String(required=True)
    user_type = String(required=True)
    phone_number = String()
    address = String()

class ChickenHouseInput(InputObjectType):
    name = String(required=True)
    house_type = String(required=True)
    capacity = Int(required=True)
    worker_id = ID()
    notes = String()

class ChickenInput(InputObjectType):
    chicken_house_id = ID(required=True)
    chicken_type = String(required=True)
    gender = String()
    date_of_birth = Date()
    notes = String()

class VaccineInput(InputObjectType):
    name = String(required=True)
    description = String()
    recommended_age_days = Int(required=True)

class VaccinationRecordInput(InputObjectType):
    chicken_house_id = ID(required=True)
    vaccine_id = ID(required=True)
    date_administered = Date(required=True)
    notes = String()

class EggCollectionInput(InputObjectType):
    chicken_house_id = ID(required=True)
    collection_date = Date(required=True)
    total_eggs = Int(required=True)
    broken_eggs = Int()
    notes = String()

class FoodInput(InputObjectType):
    name = String(required=True)
    description = String()
    unit = String(required=True)

class FoodPurchaseInput(InputObjectType):
    food_id = ID(required=True)
    quantity = Float(required=True)
    unit_price = Float(required=True)
    purchase_date = Date()
    supplier = String()
    receipt_number = String()
    notes = String()

class FoodDistributionInput(InputObjectType):
    chicken_house_id = ID(required=True)
    food_id = ID(required=True)
    quantity = Float(required=True)
    distribution_date = DateTime()
    notes = String()

class SaleInput(InputObjectType):
    sale_type = String(required=True)
    customer_id = ID()
    sales_manager_id = ID(required=True)
    sale_date = DateTime()
    total_amount = Float(required=True)
    payment_received = Boolean()
    payment_method = String()
    notes = String()

class SaleItemInput(InputObjectType):
    sale_id = ID(required=True)
    egg_trays = Int()
    egg_singles = Int()
    egg_price_per_tray = Float()
    chicken_id = ID()
    chicken_price = Float()
    item_description = String()
    quantity = Float()
    unit_price = Float()

class ExpenseInput(InputObjectType):
    expense_type = String(required=True)
    amount = Float(required=True)
    date = Date()
    description = String(required=True)

class HealthReportInput(InputObjectType):
    chicken_house_id = ID(required=True)
    report_date = Date()
    healthy_count = Int(required=True)
    sick_count = Int(required=True)
    symptoms = String()
    treatment = String()
    notes = String()

class InventoryUpdateInput(InputObjectType):
    egg_count = Int(required=True)