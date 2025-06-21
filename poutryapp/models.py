from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager

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
        ('SALES_MANAGER', 'Doctor'),
    )

    username = None  # Remove username field
    phone_number = models.CharField(max_length=15, unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['user_type']

    objects = CustomUserManager()  # Set custom manager here

    def __str__(self):
        return f"{self.get_full_name()} ({self.phone_number})"


class ChickenHouse(models.Model):
    name = models.CharField(max_length=100, unique=True)
    capacity = models.PositiveIntegerField(help_text="Maximum number of chickens this house can hold")
    current_chicken_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='chicken_houses')
    
    def __str__(self):
        return f"{self.name} (Capacity: {self.capacity})"

class EggCollection(models.Model):
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collected_eggs')
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE)
    date_collected = models.DateField(default=timezone.now)
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
        return f"{self.chicken_house.name} - {self.total_eggs} eggs on {self.date_collected}"

class EggInventory(models.Model):
    total_eggs = models.PositiveIntegerField(default=0)
    rejected_eggs = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Inventory: {self.total_eggs} eggs ({self.rejected_eggs} rejected)"

class EggSale(models.Model):
    date_sold = models.DateField(default=timezone.now)
    quantity = models.PositiveIntegerField()
    price_per_egg = models.DecimalField(max_digits=10, decimal_places=2)
    buyer_name = models.CharField(max_length=100)
    buyer_contact = models.CharField(max_length=20, blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    def __str__(self):
        return f"Sold {self.quantity} eggs on {self.date_sold}"

class FoodType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class FoodInventory(models.Model):
    food_type = models.ForeignKey(FoodType, on_delete=models.CASCADE)
    sacks_in_stock = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Food Inventories"
    
    def __str__(self):
        return f"{self.food_type}: {self.sacks_in_stock} sacks"

class FoodPurchase(models.Model):
    food_type = models.ForeignKey(FoodType, on_delete=models.CASCADE)
    sacks_purchased = models.PositiveIntegerField()
    price_per_sack = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.CharField(max_length=100)
    purchase_date = models.DateField(default=timezone.now)
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    def __str__(self):
        return f"{self.sacks_purchased} sacks of {self.food_type} on {self.purchase_date}"

class FoodDistribution(models.Model):
    food_type = models.ForeignKey(FoodType, on_delete=models.CASCADE)
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE)
    sacks_distributed = models.PositiveIntegerField()
    date_distributed = models.DateField(default=timezone.now)
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
        return f"{self.sacks_distributed} sacks to {self.chicken_house.name} on {self.date_distributed}"

class Medicine(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    unit_of_measure = models.CharField(max_length=20, help_text="e.g., ml, tablets, kg")
    
    def __str__(self):
        return self.name

class MedicineInventory(models.Model):
    medicine = models.OneToOneField(Medicine, on_delete=models.CASCADE)
    quantity_in_stock = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Medicine Inventories"
    
    def __str__(self):
        return f"{self.medicine}: {self.quantity_in_stock} {self.medicine.unit_of_measure}"

class MedicinePurchase(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.CharField(max_length=100)
    purchase_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField()
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    def __str__(self):
        return f"{self.quantity} {self.medicine.unit_measure} of {self.medicine} on {self.purchase_date}"

class MedicineDistribution(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    date_distributed = models.DateField(default=timezone.now)
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

class ChickenDeathRecord(models.Model):
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE)
    date_recorded = models.DateField(default=timezone.now)
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
        return f"{self.number_dead} deaths in {self.chicken_house.name} on {self.date_recorded}"

# Signals
@receiver(post_save, sender=EggCollection)
def update_egg_inventory(sender, instance, created, **kwargs):
    if created:
        inventory, _ = EggInventory.objects.get_or_create(pk=1)
        inventory.total_eggs += instance.total_eggs
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

