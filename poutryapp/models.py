from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.forms import ValidationError

class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('Phone number must be set')
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, phone_number, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(phone_number, password, **extra_fields)

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('worker', 'Worker'),
        ('doctor', 'Doctor'),
        ('customer', 'Customer'),
        ('stock_manager', 'Stock Manager'),
    ]
    
    # Remove username and use phone_number instead
    username = None
    phone_number = models.CharField(max_length=15, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.phone_number} ({self.role})"

# -------------------------------
# Chicken Houses
# -------------------------------
class ChickenHouse(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255, blank=True)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return self.name

# -------------------------------
# Worker Assignments
# -------------------------------
class Assignment(models.Model):
    worker = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'worker'}
    )
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE)
    assigned_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.worker.name} → {self.chicken_house.name}"

 
# -------------------------------
# Egg Collection
# -------------------------------

class EggsCollection(models.Model):
    worker = models.ForeignKey(CustomUser, limit_choices_to={'role': 'worker'}, on_delete=models.CASCADE)
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE)
    date_collected = models.DateField()
    quantity = models.PositiveIntegerField(help_text="Number of eggs collected")

    def __str__(self):
        return f"{self.date_collected}: {self.quantity} eggs"

# -------------------------------
# Health Records
# -------------------------------

class HealthRecord(models.Model):
    doctor = models.ForeignKey(CustomUser, limit_choices_to={'role': 'doctor'}, on_delete=models.CASCADE)
    chicken_house = models.ForeignKey(ChickenHouse, on_delete=models.CASCADE)
    date = models.DateField()
    health_issue = models.TextField()
    treatment = models.TextField(blank=True, null=True)
    deaths = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.date} - {self.health_issue}"

# -------------------------------
# Product and Inventory
# -------------------------------

class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

class Store(models.Model):
    UNIT_CHOICES = [
        ('egg', 'Egg'),
        ('tray', 'Tray'),  # 36 eggs = 1 tray
        ('crate', 'Crate'),
        ('kg', 'Kilogram'),
        ('liter', 'Liter'),
    ]
    
    # Relationships
    eggs_collection = models.ForeignKey(
        EggsCollection,
        on_delete=models.CASCADE,
        related_name='store_entries',
        null=True,
        blank=True
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Egg-Specific Fields
    entry_type = models.CharField(
        max_length=20,
        choices=[('egg', 'Egg'), ('product', 'Product')],
        default='product'
    )
    
    # Good Eggs Tracking
    good_eggs = models.PositiveIntegerField(default=0)
    good_trays = models.PositiveIntegerField(default=0, editable=False)
    good_loose = models.PositiveIntegerField(default=0, editable=False)
    
    # Rejects Tracking
    broken_eggs = models.PositiveIntegerField(default=0)
    cracked_eggs = models.PositiveIntegerField(default=0)
    dirty_eggs = models.PositiveIntegerField(default=0)
    
    # General Fields
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_recorded = models.DateField(auto_now_add=True)
    quality_checker = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role__in': ['worker', 'admin']}
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_recorded']
        verbose_name = "Store Inventory"
        verbose_name_plural = "Store Inventory"

    def __str__(self):
        if self.entry_type == 'egg':
            return (f"Eggs: {self.good_trays}t {self.good_loose}l | "
                    f"Rejects: {self.total_rejects} (B:{self.broken_eggs} C:{self.cracked_eggs} D:{self.dirty_eggs})")
        return f"{self.product.name}: {self.quantity}{self.unit}"

    def save(self, *args, **kwargs):
        if self.entry_type == 'egg' and self.eggs_collection:
            # Auto-calculate good trays/loose eggs
            self.good_trays = self.good_eggs // 36
            self.good_loose = self.good_eggs % 36
            
            # Verify rejects don't exceed collected eggs
            total_eggs_recorded = (self.good_eggs + self.broken_eggs + 
                                 self.cracked_eggs + self.dirty_eggs)
            if total_eggs_recorded > self.eggs_collection.quantity:
                raise ValidationError("Total eggs recorded exceed collected quantity")
                
        super().save(*args, **kwargs)

    @property
    def total_rejects(self):
        return self.broken_eggs + self.cracked_eggs + self.dirty_eggs

    @property
    def quality_metrics(self):
        if self.entry_type != 'egg' or not self.eggs_collection:
            return None
            
        total = self.eggs_collection.quantity
        return {
            'good_percentage': (self.good_eggs / total) * 100,
            'broken_percentage': (self.broken_eggs / total) * 100,
            'cracked_percentage': (self.cracked_eggs / total) * 100,
            'dirty_percentage': (self.dirty_eggs / total) * 100
        }


# -------------------------------
# Orders
# -------------------------------

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(CustomUser, limit_choices_to={'role': 'customer'}, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Order #{self.id} - {self.product.name}"

# -------------------------------
# Feedback
# -------------------------------

class Feedback(models.Model):
    customer = models.ForeignKey(CustomUser, limit_choices_to={'role': 'customer'}, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(default=5)  # Out of 5
    comment = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.customer.name}"

