from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('worker', 'Worker'),
        ('doctor', 'Doctor'),
        ('customer', 'Customer'),
        ('stock_manager', 'Stock Manager'),
    ]
    
    # Standard Django username/password fields are inherited from AbstractUser
    # Add your custom fields
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='customer'
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        blank=True, 
        null=True
    )
    date_of_birth = models.DateField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.role})"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
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

# [Rest of your models remain the same, just change User to CustomUser]
# -------------------------------
# Worker Assignments
# -------------------------------

class Assignment(models.Model):
    worker = models.ForeignKey(CustomUser, limit_choices_to={'role': 'worker'}, on_delete=models.CASCADE)
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

class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"

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

