from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, 
    Assignment, 
    EggsCollection, 
    HealthRecord, 
    Product, 
    Store, 
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
    
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from .models import Store

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = (
        'get_entry_type',
        'get_egg_summary',
        'get_reject_summary',
        'date_recorded',
        'quality_checker',
        'get_quality_metrics',
    )
    list_filter = (
        'entry_type',
        'date_recorded',
        'quality_checker',
    )
    search_fields = (
        'eggs_collection__chicken_house__name',
        'product__name',
        'notes',
    )
    date_hierarchy = 'date_recorded'
    ordering = ('-date_recorded',)

    readonly_fields = (
        'good_trays',
        'good_loose',
        'date_recorded',
    )

    fieldsets = (
        ('Basic Information', {
            'fields': ('entry_type', 'quality_checker', 'notes', 'date_recorded'),
        }),
        ('Egg Inventory', {
            'fields': (
                'eggs_collection',
                'good_eggs',
                'good_trays',
                'good_loose',
                'broken_eggs',
                'cracked_eggs',
                'dirty_eggs',
            ),
            'classes': ('collapse',),
            'description': 'Egg-specific tracking. Good trays/loose are auto-calculated.',
        }),
        ('Product Inventory', {
            'fields': ('product', 'quantity', 'unit'),
            'classes': ('collapse',),
        }),
    )

    def get_entry_type(self, obj):
        return obj.get_entry_type_display()
    get_entry_type.short_description = 'Type'
    get_entry_type.admin_order_field = 'entry_type'

    def get_egg_summary(self, obj):
        if obj.entry_type == 'egg':
            return f"{obj.good_trays} trays, {obj.good_loose} loose"
        return f"{obj.quantity} {obj.unit}"
    get_egg_summary.short_description = 'Good Inventory'

    def get_reject_summary(self, obj):
        if obj.entry_type == 'egg':
            return f"B: {obj.broken_eggs} | C: {obj.cracked_eggs} | D: {obj.dirty_eggs}"
        return "N/A"
    get_reject_summary.short_description = 'Rejects'

    def get_quality_metrics(self, obj):
        metrics = obj.quality_metrics
        if metrics:
            try:
                return format_html(
                    "Good: <b>{:.1f}%</b><br>Broken: {:.1f}%<br>Cracked: {:.1f}%<br>Dirty: {:.1f}%",
                    float(metrics['good_percentage']),
                    float(metrics['broken_percentage']),
                    float(metrics['cracked_percentage']),
                    float(metrics['dirty_percentage']),
                )
            except (ValueError, TypeError, KeyError):
                return "Invalid data"
        return "N/A"

    get_quality_metrics.short_description = 'Quality Metrics'

    def save_model(self, request, obj, form, change):
        try:
            obj.full_clean()
        except ValidationError as e:
            form.add_error(None, e)
            return
        super().save_model(request, obj, form, change)
