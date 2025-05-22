from django.contrib import admin
from .models import User, EggsCollection, Assignment, HealthRecord, Order, Feedback, Product, ChickenHouse, Inventory

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone_number', 'role', 'is_active', 'is_admin')
    search_fields = ('name', 'phone_number', 'email')
    list_filter = ('role', 'is_active', 'is_admin')

@admin.register(ChickenHouse)
class ChickenHouseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'location', 'capacity')
    search_fields = ('name', 'location')

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'worker', 'chicken_house', 'assigned_on')
    search_fields = ('worker__name', 'chicken_house__name')
    list_filter = ('assigned_on',)

@admin.register(EggsCollection)
class EggsCollectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'worker', 'chicken_house', 'date_collected', 'quantity')
    search_fields = ('worker__name', 'chicken_house__name')
    list_filter = ('date_collected',)

@admin.register(HealthRecord)
class HealthRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'chicken_house', 'date', 'health_issue', 'deaths')
    search_fields = ('doctor__name', 'health_issue')
    list_filter = ('date',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price')
    search_fields = ('name',)

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'quantity', 'updated_at')
    search_fields = ('product__name',)
    list_filter = ('updated_at',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'product', 'quantity', 'order_date', 'status')
    search_fields = ('customer__name', 'product__name')
    list_filter = ('status', 'order_date')

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'order', 'rating', 'submitted_at')
    search_fields = ('customer__name', 'comment')
    list_filter = ('rating', 'submitted_at')
