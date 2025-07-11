import datetime
from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from django.forms.models import model_to_dict

from poutryapp.models import *

@receiver(pre_save, sender=User)
def validate_user_type(sender, instance, **kwargs):
    """
    Ensure user type is valid and workers are assigned to a chicken house.
    Runs before user is saved.
    """
    valid_types = [choice[0] for choice in User.USER_TYPE_CHOICES]
    if instance.user_type not in valid_types:
        raise ValidationError(f"Invalid user type. Must be one of: {', '.join(valid_types)}")
    
    # Workers must be assigned to a chicken house
    if instance.user_type == 'WORKER' and not hasattr(instance, 'chicken_house'):
        # raise ValidationError("Workers must be assigned to a chicken house")
        pass
    
@receiver(pre_save, sender=ChickenHouse)
def validate_chicken_house(sender, instance, **kwargs):
    """
    Validate chicken house capacity and age before saving.
    """
    if instance.current_chicken_count > instance.capacity:
        raise ValidationError("Current chicken count exceeds house capacity")
    
    if instance.age_in_weeks < 0:
        raise ValidationError("Age cannot be negative")
    
    # Ensure average weight is reasonable
    if instance.average_weight < 0 or instance.average_weight > 10:  # Assuming 10kg is max reasonable weight
        raise ValidationError("Average weight must be between 0 and 10kg")

@receiver(post_save, sender=ChickenDeathRecord)
def update_chicken_count_on_death(sender, instance, created, **kwargs):
    """
    Update chicken house count when deaths are confirmed by doctor.
    """
    if instance.confirmed_by and instance.confirmed_by.user_type == 'DOCTOR':
        with transaction.atomic():
            house = instance.chicken_house
            if house.current_chicken_count >= instance.number_dead:
                house.current_chicken_count -= instance.number_dead
                house.save()
            else:
                house.current_chicken_count = 0
                house.save()
       
    
@receiver(pre_save, sender=EggCollection)
def validate_egg_collection(sender, instance, **kwargs):
    """
    Validate egg collection before saving and set confirmation date.
    """
    if instance.pk and instance.stock_manager_confirmed:
        original = EggCollection.objects.get(pk=instance.pk)
        if not original.stock_manager_confirmed:
            instance.stock_manager_confirmation_date = timezone.now()

@receiver(post_save, sender=EggCollection)
def update_inventory_on_collection(sender, instance, created, **kwargs):
    """
    Update egg inventory when new collection is confirmed.
    """
    if instance.stock_manager_confirmed:
        with transaction.atomic():
            inventory, _ = EggInventory.objects.get_or_create(pk=1)
            inventory.total_eggs += instance.total_eggs
            inventory.rejected_eggs += instance.rejected_eggs
            inventory.save()
           

@receiver(post_save, sender=EggDistribution)
def update_inventories_on_distribution(sender, instance, created, **kwargs):
    """
    Update both main and sales manager inventories when eggs are distributed.
    """
    if created:
        with transaction.atomic():
            # Main inventory update
            main_inventory = EggInventory.objects.first()
            if main_inventory.total_eggs < instance.quantity:
                raise ValidationError("Not enough eggs in main inventory for distribution")
            
            main_inventory.total_eggs -= instance.quantity
            main_inventory.save()
            
            # Sales manager inventory update
            sm_inventory, _ = SalesManagerInventory.objects.get_or_create(
                sales_manager=instance.sales_manager
            )
            sm_inventory.total_eggs += instance.quantity
            sm_inventory.save()
            

@receiver(pre_save, sender=EggSale)
def validate_egg_sale(sender, instance, **kwargs):
    """
    Validate egg sale against available inventory before saving.
    """
    if instance.pk is None:  # New sale
        try:
            sm_inventory = SalesManagerInventory.objects.get(
                sales_manager=instance.sales_manager
            )
            if sm_inventory.remaining_eggs < instance.quantity:
                raise ValidationError(
                    f"Not enough eggs in inventory. Available: {sm_inventory.remaining_eggs}, Requested: {instance.quantity}"
                )
        except SalesManagerInventory.DoesNotExist:
            raise ValidationError("Sales manager has no inventory record")

@receiver(post_save, sender=EggSale)
def update_inventory_on_sale(sender, instance, created, **kwargs):
    """
    Update sales manager inventory when eggs are sold.
    """
    if created and instance.confirmed:
        with transaction.atomic():
            sm_inventory = SalesManagerInventory.objects.get(
                sales_manager=instance.sales_manager
            )
            sm_inventory.sold_eggs += instance.quantity
            sm_inventory.save()
            
            
@receiver(post_save, sender=FoodPurchase)
def update_food_inventory_on_purchase(sender, instance, created, **kwargs):
    """
    Update food inventory when new purchase is made.
    """
    if created:
        with transaction.atomic():
            inventory, _ = FoodInventory.objects.get_or_create(
                food_type=instance.food_type
            )
            inventory.sacks_in_stock += instance.sacks_purchased
            inventory.save()
            

@receiver(pre_save, sender=FoodDistribution)
def validate_food_distribution(sender, instance, **kwargs):
    """
    Validate food distribution and update inventory when confirmed.
    """
    if instance.pk:  # Only for updates
        original = FoodDistribution.objects.get(pk=instance.pk)
        if not original.worker_confirmed and instance.worker_confirmed:
            instance.confirmation_date = timezone.now()
            
            with transaction.atomic():
                inventory = FoodInventory.objects.get(food_type=instance.food_type)
                if inventory.sacks_in_stock < instance.sacks_distributed:
                    raise ValidationError(
                        f"Not enough {instance.food_type.name} in inventory. Available: {inventory.sacks_in_stock}, Requested: {instance.sacks_distributed}"
                    )
                
                inventory.sacks_in_stock -= instance.sacks_distributed
                inventory.save()
                

@receiver(post_save, sender=MedicinePurchase)
def update_medicine_inventory_on_purchase(sender, instance, created, **kwargs):
    """
    Update medicine inventory when new purchase is made.
    """
    if created:
        with transaction.atomic():
            inventory, created = MedicineInventory.objects.get_or_create(
                medicine=instance.medicine,
                defaults={'quantity_in_stock': 0}
            )
            inventory.quantity_in_stock += instance.quantity
            inventory.save()
            

@receiver(pre_save, sender=MedicineDistribution)
def validate_medicine_distribution(sender, instance, **kwargs):
    """
    Validate medicine distribution and update inventory when confirmed.
    """
    if instance.pk:  # Only for updates
        original = MedicineDistribution.objects.get(pk=instance.pk)
        
        # Check if confirmation status changed
        doctor_confirmed = (not original.doctor_confirmed and instance.doctor_confirmed)
        worker_confirmed = (not original.worker_confirmed and instance.worker_confirmed)
        
        if doctor_confirmed or worker_confirmed:
            with transaction.atomic():
                inventory = MedicineInventory.objects.get(medicine=instance.medicine)
                if inventory.quantity_in_stock < instance.quantity:
                    raise ValidationError(
                        f"Not enough {instance.medicine.name} in inventory. Available: {inventory.quantity_in_stock}, Requested: {instance.quantity}"
                    )
                
                # Only deduct when both are confirmed
                if instance.doctor_confirmed and instance.worker_confirmed:
                    inventory.quantity_in_stock -= instance.quantity
                    inventory.save()
                    
                    
@receiver(pre_save, sender=Expense)
def calculate_expense_total(sender, instance, **kwargs):
    """
    Automatically calculate total cost before saving expense.
    """
    instance.total_cost = Decimal(instance.unit_cost) * Decimal(instance.quantity)

@receiver(pre_save, sender=SalaryPayment)
def validate_salary_payment(sender, instance, **kwargs):
    """
    Validate salary payment before saving.
    """
    if instance.period_start > instance.period_end:
        raise ValidationError("Period start date must be before end date")
    
    if instance.worker.user_type != 'WORKER':
        raise ValidationError("Can only pay salaries to workers")
    
    if instance.amount <= 0:
        raise ValidationError("Salary amount must be positive")
  