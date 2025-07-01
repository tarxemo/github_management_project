from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager


class ActiveManager(models.Manager):
    def active(self):
        return self.get_queryset().filter(is_active=True)

    def inactive(self):
        return self.get_queryset().filter(is_active=False)

    def all_objects(self):
        return self.get_queryset()

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set when created
    updated_at = models.DateTimeField(auto_now=True)      # Automatically updated on save
    is_active = models.BooleanField(default=True)

    # Attach the custom manager
    objects = ActiveManager()

    class Meta:
        abstract = True
        
class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The phone number must be set')
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number, password, **extra_fields)

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('STOCK_MANAGER', 'Stock Manager'),
        ('WORKER', 'Worker'),
        ('DOCTOR', 'Doctor'),
        ('SALES_MANAGER', 'Sales Manager'),
    )

    username = None  # Remove username field
    phone_number = models.CharField(max_length=15, unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['user_type']

    objects = CustomUserManager()  # Set custom manager here

    def __str__(self):
        return f"{self.get_full_name()} ({self.phone_number})"

class SystemLog(models.Model):
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    changes = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'System Log'
        verbose_name_plural = 'System Logs'

    def __str__(self):
        return f"{self.get_action_display()} on {self.model_name} by {self.user} at {self.timestamp}"

class AuditLogMixin:
    def save(self, *args, **kwargs):
        """Override save to capture state before save"""
        if self.pk:  # Only for updates, not creates
            # Get the current state from DB
            old_instance = self.__class__.objects.get(pk=self.pk)
            self._pre_save_state = {}
            for field in self._meta.fields:
                self._pre_save_state[field.name] = getattr(old_instance, field.name)
        super().save(*args, **kwargs)
        
        
class ChickenHouse(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    capacity = models.PositiveIntegerField(help_text="Maximum number of chickens this house can hold")
    current_chicken_count = models.PositiveIntegerField(default=0)
    owner = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='chicken_houses')

    # 🐣 Add these:
    age_in_weeks = models.PositiveIntegerField(default=0)
    average_weight = models.FloatField(help_text="Average weight per chicken in kg", default=0.0)

    def __str__(self):
        return f"{self.name} (Age: {self.age_in_weeks} weeks, Weight: {self.average_weight}kg)"



class EggCollection(BaseModel):
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collected_eggs')
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE)
    full_trays = models.PositiveIntegerField(help_text="Number of full trays (30 eggs per tray)")
    loose_eggs = models.PositiveIntegerField(default=0, help_text="Eggs not fitting in full trays")
    rejected_eggs = models.PositiveIntegerField(default=0, help_text="Eggs not fit for sale")
    stock_manager_confirmed = models.BooleanField(default=False)
    stock_manager_confirmation_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    @property
    def total_eggs(self):
        return (self.full_trays * 30) + self.loose_eggs
    
    def clean(self):
        if self.worker.user_type != 'WORKER':
            raise ValidationError("Only workers can collect eggs")
        if self.chicken_house != self.worker.chicken_house:
            raise ValidationError("Worker can only collect eggs from their assigned chicken house")
    
    def __str__(self):
        return f"{self.chicken_house.name} - {self.total_eggs} eggs on {self.created_at}"

class EggInventory(BaseModel):
    total_eggs = models.PositiveIntegerField(default=0)
    rejected_eggs = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Inventory: {self.total_eggs} eggs ({self.rejected_eggs} rejected)"

class EggSale(BaseModel):
    quantity = models.PositiveIntegerField()
    remained_eggs = models.PositiveIntegerField(default=0)
    rejected_eggs = models.PositiveIntegerField(default=0)
    price_per_egg = models.DecimalField(max_digits=10, decimal_places=2)
    buyer_name = models.CharField(max_length=100)
    buyer_contact = models.CharField(max_length=20, blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    confirm_received = models.BooleanField(default=False)
    confirm_sales = models.BooleanField(default=False)
    def __str__(self):
        return f"Sold {self.quantity} eggs on {self.created_at}"

class FoodType(BaseModel):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class FoodInventory(BaseModel):
    food_type = models.ForeignKey(FoodType, on_delete=models.CASCADE)
    sacks_in_stock = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Food Inventories"
    
    def __str__(self):
        return f"{self.food_type}: {self.sacks_in_stock} sacks"

class FoodPurchase(BaseModel):
    food_type = models.ForeignKey(FoodType, on_delete=models.CASCADE)
    sacks_purchased = models.PositiveIntegerField()
    price_per_sack = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.CharField(max_length=100)
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    def __str__(self):
        return f"{self.sacks_purchased} sacks of {self.food_type} on {self.created_at}"

class FoodDistribution(BaseModel):
    food_type = models.ForeignKey(FoodType, on_delete=models.CASCADE)
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE)
    sacks_distributed = models.DecimalField(max_digits=10, decimal_places=2)
    distributed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='distributed_food')
    received_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='received_food')
    worker_confirmed = models.BooleanField(default=False)
    confirmation_date = models.DateTimeField(null=True, blank=True)
    
    def clean(self):
        if self.distributed_by.user_type != 'STOCK_MANAGER':
            raise ValidationError("Only stock managers can distribute food")
        if self.received_by.user_type != 'WORKER':
            raise ValidationError("Only workers can receive food")
        if self.chicken_house != self.received_by.chicken_house:
            raise ValidationError("Worker can only receive food for their assigned chicken house")
    
    def __str__(self):
        return f"{self.sacks_distributed} sacks to {self.chicken_house.name} on {self.created_at}"

class Medicine(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    unit_of_measure = models.CharField(max_length=20, help_text="e.g., ml, tablets, kg")
    
    def __str__(self):
        return self.name

class MedicineInventory(BaseModel):
    medicine = models.OneToOneField(Medicine, on_delete=models.CASCADE)
    quantity_in_stock = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name_plural = "Medicine Inventories"
    
    def __str__(self):
        return f"{self.medicine}: {self.quantity_in_stock} {self.medicine.unit_of_measure}"

class MedicinePurchase(BaseModel):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.CharField(max_length=100)
    expiry_date = models.DateField()
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    def __str__(self):
        return f"{self.quantity} {self.medicine.unit_measure} of {self.medicine} on {self.created_at}"

class MedicineDistribution(BaseModel):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    distributed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='distributed_medicine')
    received_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='received_medicine')
    doctor_confirmed = models.BooleanField(default=False)
    worker_confirmed = models.BooleanField(default=False)
    purpose = models.TextField(blank=True)
    
    def clean(self):
        if self.distributed_by.user_type != 'STOCK_MANAGER':
            raise ValidationError("Only stock managers can distribute medicine")
        if self.received_by.user_type not in ['DOCTOR', 'WORKER']:
            raise ValidationError("Only doctors or workers can receive medicine")
    
    def __str__(self):
        return f"{self.quantity} {self.medicine.unit_of_measure} to {self.chicken_house.name}"

class ChickenDeathRecord(BaseModel):
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE)
    number_dead = models.PositiveIntegerField()
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='recorded_deaths')
    confirmed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='confirmed_deaths', null=True, blank=True)
    notes = models.TextField(blank=True)
    doctor_notes = models.TextField(blank=True)
    possible_cause = models.CharField(max_length=100, blank=True)
    
    def clean(self):
        if self.recorded_by.user_type != 'WORKER':
            raise ValidationError("Only workers can record chicken deaths")
        if self.confirmed_by and self.confirmed_by.user_type != 'DOCTOR':
            raise ValidationError("Only doctors can confirm death records")
    
    def __str__(self):
        return f"{self.number_dead} deaths in {self.chicken_house.name} on {self.created_at}"
    
class ExpenseCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class Expense(BaseModel):
    PAYMENT_METHOD_CHOICES = (
        ('CASH', 'Cash'),
        ('MPESA', 'M-Pesa'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
    )
    
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT)
    description = models.TextField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='CASH')
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="Cost per unit")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1, help_text="Number of units")
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    receipt_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def clean(self):
        # Calculate total cost before saving
        self.total_cost = self.unit_cost * self.quantity
    
    def save(self, *args, **kwargs):
        self.full_clean()  # This will call clean() and validate the model
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.category.name} - {self.total_cost} on {self.date}"

class SalaryPayment(BaseModel):
    worker = models.ForeignKey(User, on_delete=models.PROTECT, limit_choices_to={'user_type': 'WORKER'})
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=Expense.PAYMENT_METHOD_CHOICES, default='CASH')
    period_start = models.DateField()
    period_end = models.DateField()
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='recorded_salaries')
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def clean(self):
        if self.period_start > self.period_end:
            raise ValidationError("Period start date must be before end date")
        if self.worker.user_type != 'WORKER':
            raise ValidationError("Can only pay salaries to workers")
    
    def __str__(self):
        return f"Salary for {self.worker.get_full_name()} - {self.amount}"
    
# Signals
@receiver(post_save, sender=EggCollection)
def update_egg_inventory(sender, instance, created, **kwargs):
    if created:
        inventory, _ = EggInventory.objects.get_or_create(pk=1)
        inventory.total_eggs += instance.total_eggs
        inventory.rejected_eggs += instance.rejected_eggs
        inventory.save()

@receiver(pre_save, sender=EggSale)
def add_back_remained_eggs_on_confirmation(sender, instance, **kwargs):
    if not instance.pk:  # Skip if it's a new object
        return

    try:
        old_instance = EggSale.objects.get(pk=instance.pk)
    except EggSale.DoesNotExist:
        return

    # If confirm_sales just changed from False to True
    if not old_instance.confirm_sales and instance.confirm_sales:
        inventory = EggInventory.objects.first()
        if inventory:
            inventory.total_eggs += instance.remained_eggs
            inventory.rejected_eggs += instance.rejected_eggs
            inventory.save()
            
@receiver(post_save, sender=EggSale)
def deduct_sold_eggs(sender, instance, created, **kwargs):
    if created:
        inventory = EggInventory.objects.first()
        if inventory:
            if inventory.total_eggs >= instance.quantity:
                inventory.total_eggs -= instance.quantity
                inventory.save()
            else:
                raise ValidationError("Not enough eggs in inventory for this sale")

@receiver(post_save, sender=FoodPurchase)
def update_food_inventory(sender, instance, created, **kwargs):
    if created:
        inventory, _ = FoodInventory.objects.get_or_create(food_type=instance.food_type)
        inventory.sacks_in_stock += instance.sacks_purchased
        inventory.save()

@receiver(pre_save, sender=FoodDistribution)
def deduct_food_on_worker_confirmation(sender, instance, **kwargs):
    if not instance.pk:
        return  # Skip new instance, wait for update

    try:
        old_instance = FoodDistribution.objects.get(pk=instance.pk)
    except FoodDistribution.DoesNotExist:
        return

    # If confirmation just changed from False → True
    if not old_instance.worker_confirmed and instance.worker_confirmed:
        inventory = FoodInventory.objects.get(food_type=instance.food_type)
        if inventory.sacks_in_stock >= instance.sacks_distributed:
            inventory.sacks_in_stock -= instance.sacks_distributed
            inventory.save()
        else:
            raise ValidationError("Not enough food in inventory for this distribution")


@receiver(post_save, sender=MedicinePurchase)
def update_medicine_inventory(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        # Try to get the existing inventory
        inventory = MedicineInventory.objects.get(medicine=instance.medicine)
        inventory.quantity_in_stock += instance.quantity
        inventory.save()
    except MedicineInventory.DoesNotExist:
        # If it doesn't exist, create a new inventory record
        MedicineInventory.objects.create(
            medicine=instance.medicine,
            quantity_in_stock=instance.quantity
        )

@receiver(pre_save, sender=MedicineDistribution)
def deduct_distributed_medicine_on_confirm(sender, instance, **kwargs):
    if not instance.pk:
        return  # Skip if it's a new object; handle after save

    try:
        previous = MedicineDistribution.objects.get(pk=instance.pk)
    except MedicineDistribution.DoesNotExist:
        return

    # If both doctor and worker confirmation just changed to True
    if (not previous.doctor_confirmed and instance.doctor_confirmed) or \
       (not previous.worker_confirmed and instance.worker_confirmed):

        # Only act if now both are confirmed
        if instance.doctor_confirmed and instance.worker_confirmed:
            inventory = MedicineInventory.objects.get(medicine=instance.medicine)
            if inventory.quantity_in_stock >= instance.quantity:
                inventory.quantity_in_stock -= instance.quantity
                inventory.save()
            else:
                raise ValidationError("Not enough medicine in inventory for this distribution")


@receiver(pre_save, sender=EggCollection)
def validate_egg_collection(sender, instance, **kwargs):
    if instance.stock_manager_confirmed and not instance.stock_manager_confirmation_date:
        instance.stock_manager_confirmation_date = timezone.now()

@receiver(pre_save, sender=FoodDistribution)
def validate_food_distribution(sender, instance, **kwargs):
    if instance.worker_confirmed and not instance.confirmation_date:
        instance.confirmation_date = timezone.now()

@receiver(pre_save, sender=ChickenDeathRecord)
def decrease_chicken_count_on_confirmation(sender, instance, **kwargs):
    if not instance.pk:
        # New record, wait until confirmed
        return

    try:
        old_instance = ChickenDeathRecord.objects.get(pk=instance.pk)
    except ChickenDeathRecord.DoesNotExist:
        return

    # If confirmed_by changed from None → someone
    if old_instance.confirmed_by is None and instance.confirmed_by is not None:
        # Make sure it's actually a doctor
        if instance.confirmed_by.user_type != 'DOCTOR':
            raise ValidationError("Only doctors can confirm death records.")

        house = instance.chicken_house
        if house.current_chicken_count >= instance.number_dead:
            house.current_chicken_count -= instance.number_dead
        else:
            house.current_chicken_count = 0
        house.save()

