from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.conf import settings

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.forms import ValidationError
from django.db import models
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum  # Add this import




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

    # Assign a worker directly
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'worker'},
        related_name='chicken_houses',
        help_text="Assign a worker to this chicken house"
    )

    def __str__(self):
        return self.name
 
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
    PRODUCT_TYPE_CHOICES = [
        ('meat', 'Meat'),
        ('eggs', 'Eggs'),
        ('layer', 'Layer'),
        ('dual', 'Dual'),
        ('broiler', 'Broiler'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default='meat')

    def __str__(self):
        return self.name



from django.db import models
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal
from django.db.models import Sum

class Store(models.Model):
    UNIT_CHOICES = [
        ('number', 'Number'),       # Simple count (whole numbers)
        ('egg', 'Egg'),             # Individual eggs
        ('tray', 'Tray (36 eggs)'), # Standard egg tray
        ('crate', 'Crate'),         # Larger container
        ('kg', 'Kilogram'),         # Weight measurement
        ('liter', 'Liter'),         # Volume measurement
        ('box', 'Box'),             # Generic container
        ('pack', 'Pack'),           # Packaged units
    ]

    # Relationships
    eggs_collection = models.ForeignKey(
        'EggsCollection',
        on_delete=models.CASCADE,
        related_name='store_entries',
        null=True,
        blank=True
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Entry Type
    ENTRY_TYPES = [
        ('egg', 'Egg'),
        ('product', 'Product'),
    ]
    entry_type = models.CharField(
        max_length=20,
        choices=ENTRY_TYPES,
        default='product'
    )

    # Inventory Tracking
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default='number'
    )

    # Egg-Specific Fields (only relevant when entry_type='egg')
    good_eggs = models.PositiveIntegerField(default=0)
    good_trays = models.PositiveIntegerField(default=0, editable=False)
    good_loose = models.PositiveIntegerField(default=0, editable=False)
    broken_eggs = models.PositiveIntegerField(default=0)
    cracked_eggs = models.PositiveIntegerField(default=0)
    dirty_eggs = models.PositiveIntegerField(default=0)

    # Metadata
    date_recorded = models.DateField(auto_now_add=True)
    quality_checker = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role__in': ['worker', 'admin']}
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_recorded']
        verbose_name = "Inventory Record"
        verbose_name_plural = "Inventory Records"
        indexes = [
            models.Index(fields=['entry_type']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        if self.entry_type == 'egg':
            return f"Eggs: {self.good_trays}t {self.good_loose}l (Total: {self.good_eggs})"
        unit_display = '' if self.unit == 'number' else f" {self.unit}"
        return f"{self.product.name}: {self.quantity}{unit_display}"

    def clean(self):
        """Validate the inventory record before saving"""
        if self.entry_type == 'egg':
            if not self.eggs_collection:
                raise ValidationError("Egg entries require an eggs collection reference")
            if self.product:
                raise ValidationError("Egg entries shouldn't have a product association")
            
            # Validate egg quantities
            if self.good_eggs < 0 or self.broken_eggs < 0 or self.cracked_eggs < 0 or self.dirty_eggs < 0:
                raise ValidationError("Egg counts cannot be negative")
        else:
            if not self.product:
                raise ValidationError("Product entries require a product selection")
            if self.eggs_collection:
                raise ValidationError("Product entries shouldn't have an eggs collection reference")
            
            # Validate quantity for 'number' units
            if self.unit == 'number' and self.quantity != self.quantity.to_integral_value():
                raise ValidationError({"quantity": "Quantity must be a whole number when unit is 'Number'"})

    def save(self, *args, **kwargs):
        """Custom save logic"""
        self.clean()  # Run validation before saving
        
        # Egg-specific calculations
        if self.entry_type == 'egg':
            self.good_trays = self.good_eggs // 36
            self.good_loose = self.good_eggs % 36
            
            total_recorded = (self.good_eggs + self.broken_eggs + 
                            self.cracked_eggs + self.dirty_eggs)
            if self.eggs_collection and total_recorded > self.eggs_collection.quantity:
                raise ValidationError("Total eggs recorded exceeds collected quantity")
        
        # Ensure whole numbers for 'number' units
        if self.unit == 'number':
            self.quantity = self.quantity.to_integral_value()
            
        super().save(*args, **kwargs)

    @property
    def total_rejects(self):
        """Calculate total rejected eggs"""
        return self.broken_eggs + self.cracked_eggs + self.dirty_eggs if self.entry_type == 'egg' else 0

    @property
    def display_quantity(self):
        """Formatted quantity display"""
        if self.entry_type == 'egg':
            return f"{self.good_eggs} eggs"
        return f"{self.quantity} {self.unit}" if self.unit != 'number' else f"{self.quantity}"

    @classmethod
    @transaction.atomic
    def deduct_inventory(cls, product, quantity):
        """Deduct inventory with proper type handling"""
        try:
            quantity = Decimal(str(quantity))
            
            if product.product_type == 'eggs':
                entries = cls.objects.filter(
                    entry_type='egg',
                    good_eggs__gt=0
                ).order_by('date_recorded')
                
                total_available = sum(Decimal(str(e.good_eggs)) for e in entries)
                if total_available < quantity:
                    raise ValidationError(f"Insufficient eggs. Available: {total_available}, Requested: {quantity}")
                
                remaining = quantity
                for entry in entries:
                    if remaining <= 0:
                        break
                    deduct = min(remaining, Decimal(str(entry.good_eggs)))
                    entry.good_eggs -= int(deduct)
                    remaining -= deduct
                    entry.save()
            else:
                entries = cls.objects.filter(
                    entry_type='product',
                    product=product,
                    quantity__gt=0
                ).order_by('date_recorded')
                
                total_available = sum(e.quantity for e in entries)
                if total_available < quantity:
                    raise ValidationError(f"Insufficient {product.name}. Available: {total_available}, Requested: {quantity}")
                
                remaining = quantity
                for entry in entries:
                    if remaining <= 0:
                        break
                    deduct = min(remaining, entry.quantity)
                    entry.quantity -= deduct
                    if entry.unit == 'number':
                        entry.quantity = entry.quantity.to_integral_value()
                    remaining -= deduct
                    entry.save()
                    
        except Exception as e:
            raise ValidationError(str(e))


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    validators=[MinValueValidator(Decimal('0.01'))]
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    sale_date = models.DateTimeField(auto_now_add=True)
    stock_manager = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'role': 'stock_manager'}
    )
    stock_deducted = models.BooleanField(default=False)

    def clean(self):
        if self.product.product_type == 'eggs' and self.quantity != int(self.quantity):
            raise ValidationError("Egg quantity must be a whole number")

    def save(self, *args, **kwargs):
        if not self.pk or not self.stock_deducted:
            Store.deduct_inventory(self.product, self.quantity)
            self.stock_deducted = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Sale {self.id} - {self.product.name}"
    


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(
        'CustomUser',
        limit_choices_to={'role': 'customer'},
        on_delete=models.PROTECT
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    stock_deducted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-order_date']

    def __str__(self):
        return f"Order {self.id} - {self.product.name}"

    def clean(self):
        if self.product.product_type == 'eggs' and self.quantity != int(self.quantity):
            raise ValidationError("Egg quantity must be a whole number")

    def save(self, *args, **kwargs):
        status_changed = False
        if self.pk:
            original = Order.objects.get(pk=self.pk)
            status_changed = original.status != self.status
        
        if status_changed and self.status in ['shipped', 'delivered', 'completed']:
            if not self.stock_deducted:
                Store.deduct_inventory(self.product, self.quantity)
                self.stock_deducted = True
        
        super().save(*args, **kwargs)

        
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

