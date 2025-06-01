from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

class User(AbstractUser):
    USER_TYPES = (
        ('ADMIN', 'Admin'),
        ('DOCTOR', 'Doctor'),
        ('WORKER', 'Worker'),
        ('SALES_MANAGER', 'Sales Manager'),
        ('CUSTOMER', 'Customer'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    phone_number = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

class ChickenHouse(models.Model):
    HOUSE_TYPES = (
        ('BROILER', 'Broiler'),
        ('LAYER', 'Layer'),
        ('BROODER', 'Brooder'),
    )
    
    name = models.CharField(max_length=100)
    house_type = models.CharField(max_length=20, choices=HOUSE_TYPES)
    capacity = models.PositiveIntegerField(help_text="Maximum number of chickens this house can hold")
    current_chicken_count = models.PositiveIntegerField(default=0)
    worker = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                              limit_choices_to={'user_type': 'WORKER'})
    created_at = models.DateTimeField(auto_now_add=True)
    last_cleaned = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    def clean(self):
        if self.current_chicken_count > self.capacity:
            raise ValidationError("Current chicken count cannot exceed house capacity")
    
    def __str__(self):
        return f"{self.name} ({self.get_house_type_display()}) - {self.current_chicken_count}/{self.capacity}"

class Chicken(models.Model):
    CHICKEN_TYPES = (
        ('BROILER', 'Broiler'),
        ('LAYER', 'Layer'),
    )
    
    GENDER_CHOICES = (
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('UNKNOWN', 'Unknown'),
    )
    
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE, related_name='chickens')
    chicken_type = models.CharField(max_length=20, choices=CHICKEN_TYPES)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='UNKNOWN')
    date_added = models.DateField(auto_now_add=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_alive = models.BooleanField(default=True)
    date_of_death = models.DateField(null=True, blank=True)
    cause_of_death = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        status = "Alive" if self.is_alive else f"Died on {self.date_of_death}"
        return f"{self.get_chicken_type_display()} - {status} (House: {self.chicken_house.name})"

class Vaccine(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    recommended_age_days = models.PositiveIntegerField(help_text="Recommended age in days for vaccination")
    
    def __str__(self):
        return self.name

class VaccinationRecord(models.Model):
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE, related_name='vaccinations')
    vaccine = models.ForeignKey(Vaccine, on_delete=models.CASCADE)
    date_administered = models.DateField()
    administered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                      limit_choices_to={'user_type': 'DOCTOR'})
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.vaccine.name} for {self.chicken_house.name} on {self.date_administered}"

class EggCollection(models.Model):
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE, related_name='egg_collections')
    collection_date = models.DateField(default=timezone.now)
    collected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                    limit_choices_to={'user_type': 'WORKER'})
    total_eggs = models.PositiveIntegerField()
    broken_eggs = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    
    def clean(self):
        if self.broken_eggs > self.total_eggs:
            raise ValidationError("Broken eggs cannot exceed total eggs collected")
    
    def calculate_full_trays(self):
        return self.total_eggs // 30
    
    def calculate_remaining_eggs(self):
        return self.total_eggs % 30
    
    def __str__(self):
        return f"{self.total_eggs} eggs from {self.chicken_house.name} on {self.collection_date}"

class Food(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(max_length=20, default='kg')
    
    def __str__(self):
        return self.name

class FoodPurchase(models.Model):
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateField(default=timezone.now)
    supplier = models.CharField(max_length=100, blank=True, null=True)
    receipt_number = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    @property
    def total_cost(self):
        return self.quantity * self.unit_price
    
    def __str__(self):
        return f"{self.quantity}{self.food.unit} of {self.food.name} on {self.purchase_date}"

class FoodDistribution(models.Model):
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE, related_name='food_distributions')
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    distribution_date = models.DateTimeField(default=timezone.now)
    distributed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                      limit_choices_to={'user_type__in': ['ADMIN', 'WORKER']})
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.quantity}{self.food.unit} of {self.food.name} to {self.chicken_house.name}"

class Inventory(models.Model):
    egg_count = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Inventory: {self.egg_count} eggs as of {self.last_updated}"

class Sale(models.Model):
    SALE_TYPES = (
        ('EGG', 'Egg'),
        ('CHICKEN', 'Chicken'),
        ('MEAT', 'Meat'),
        ('OTHER', 'Other'),
    )
    
    sale_type = models.CharField(max_length=20, choices=SALE_TYPES)
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="customers",
                                limit_choices_to={'user_type': 'CUSTOMER'})
    sales_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="sellers",
                                    limit_choices_to={'user_type': 'SALES_MANAGER'})
    sale_date = models.DateTimeField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_received = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.get_sale_type_display()} sale to {self.customer} on {self.sale_date}"

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    
    # For egg sales
    egg_trays = models.PositiveIntegerField(default=0)
    egg_singles = models.PositiveIntegerField(default=0)
    egg_price_per_tray = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # For chicken sales
    chicken = models.ForeignKey(Chicken, on_delete=models.SET_NULL, null=True, blank=True)
    chicken_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # For other items
    item_description = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    @property
    def total_price(self):
        if self.sale.sale_type == 'EGG':
            return (self.egg_trays * self.egg_price_per_tray) + \
                   (self.egg_singles * (self.egg_price_per_tray / 30))
        elif self.sale.sale_type == 'CHICKEN' and self.chicken:
            return self.chicken_price
        else:
            return self.quantity * self.unit_price
    
    def clean(self):
        if self.sale.sale_type == 'EGG' and (self.chicken or self.item_description):
            raise ValidationError("Egg sale should not have chicken or other items")
        if self.sale.sale_type == 'CHICKEN' and (self.egg_trays or self.egg_singles or self.item_description):
            raise ValidationError("Chicken sale should not have eggs or other items")
    
    def __str__(self):
        if self.sale.sale_type == 'EGG':
            return f"{self.egg_trays} trays + {self.egg_singles} eggs"
        elif self.sale.sale_type == 'CHICKEN':
            return f"Chicken {self.chicken.id if self.chicken else 'N/A'}"
        else:
            return self.item_description or "Other item"

class Expense(models.Model):
    EXPENSE_TYPES = (
        ('FOOD', 'Food'),
        ('VACCINE', 'Vaccine'),
        ('EQUIPMENT', 'Equipment'),
        ('UTILITY', 'Utility'),
        ('SALARY', 'Salary'),
        ('OTHER', 'Other'),
    )
    
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    description = models.TextField()
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                  limit_choices_to={'user_type__in': ['ADMIN', 'SALES_MANAGER']})
    
    def __str__(self):
        return f"{self.get_expense_type_display()} - {self.amount} on {self.date}"

class HealthReport(models.Model):
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE, related_name='health_reports')
    report_date = models.DateField(default=timezone.now)
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   limit_choices_to={'user_type': 'DOCTOR'})
    healthy_count = models.PositiveIntegerField()
    sick_count = models.PositiveIntegerField()
    symptoms = models.TextField(blank=True, null=True)
    treatment = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Health report for {self.chicken_house.name} on {self.report_date}"

# Signals
@receiver(post_save, sender=EggCollection)
def update_inventory_on_egg_collection(sender, instance, created, **kwargs):
    inventory, _ = Inventory.objects.get_or_create(pk=1)
    if created:
        inventory.egg_count += instance.total_eggs
        inventory.save()

@receiver(post_save, sender=SaleItem)
def update_inventory_on_sale(sender, instance, created, **kwargs):
    if instance.sale.sale_type == 'EGG':
        inventory, _ = Inventory.objects.get_or_create(pk=1)
        eggs_sold = (instance.egg_trays * 30) + instance.egg_singles
        inventory.egg_count -= eggs_sold
        inventory.save()
    elif instance.sale.sale_type == 'CHICKEN' and instance.chicken:
        instance.chicken.is_alive = False
        instance.chicken.date_of_death = instance.sale.sale_date.date()
        instance.chicken.save()
        
        # Update chicken house count
        chicken_house = instance.chicken.chicken_house
        chicken_house.current_chicken_count -= 1
        chicken_house.save()

@receiver(post_save, sender=Chicken)
def update_chicken_house_count(sender, instance, created, **kwargs):
    if created and instance.is_alive:
        chicken_house = instance.chicken_house
        chicken_house.current_chicken_count += 1
        chicken_house.save()

@receiver(post_delete, sender=Chicken)
def update_chicken_house_count_on_delete(sender, instance, **kwargs):
    if instance.is_alive:
        chicken_house = instance.chicken_house
        chicken_house.current_chicken_count -= 1
        chicken_house.save()

@receiver(pre_save, sender=FoodDistribution)
def check_food_availability(sender, instance, **kwargs):
    # This would need to be implemented with actual food inventory tracking
    pass