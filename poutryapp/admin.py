from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, 
    Assignment, 
    EggsCollection, 
    HealthRecord, 
    Product, 
    Inventory, 
    Order, 
    Feedback, 
    ChickenHouse
)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('phone_number', 'email', 'first_name', 'last_name', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('phone_number', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'role', 'profile_picture', 'date_of_birth')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'first_name', 'last_name', 'email', 'role', 'password1', 'password2'),
        }),
    )

@admin.register(ChickenHouse)
class ChickenHouseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'location', 'capacity')
    search_fields = ('name', 'location')

 
@admin.register(EggsCollection)
class EggsCollectionAdmin(admin.ModelAdmin):
    list_display = ('worker', 'chicken_house', 'date_collected', 'quantity')
    list_filter = ('date_collected',)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "worker":
            # Filter only workers
            kwargs["queryset"] = CustomUser.objects.filter(role='worker')
            # Customize how the choices are displayed
            field = super().formfield_for_foreignkey(db_field, request, **kwargs)
            field.label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.role})"
            return field
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('worker', 'chicken_house', 'assigned_on')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "worker":
            kwargs["queryset"] = CustomUser.objects.filter(role='worker')
            field = super().formfield_for_foreignkey(db_field, request, **kwargs)
            field.label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.role})"
            return field
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(HealthRecord)
class HealthRecordAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'chicken_house', 'date', 'health_issue')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "doctor":
            kwargs["queryset"] = CustomUser.objects.filter(role='doctor')
            field = super().formfield_for_foreignkey(db_field, request, **kwargs)
            field.label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.role})"
            return field
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'description')
    search_fields = ('name',)

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'updated_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('customer', 'product', 'quantity', 'order_date', 'status')
    list_filter = ('status', 'order_date')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "customer":
            kwargs["queryset"] = CustomUser.objects.filter(role='customer')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('customer', 'order', 'rating', 'submitted_at')
    list_filter = ('rating', 'submitted_at')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "customer":
            kwargs["queryset"] = CustomUser.objects.filter(role='customer')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)