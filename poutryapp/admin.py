from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, 
    EggsCollection, 
    HealthRecord, 
    Product, 
    Store, 
    Order, 
    Feedback, 
    ChickenHouse
)


from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from .models import Store
from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from .models import Product, Store, Sale, Order
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils.html import format_html

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
    list_display = ('name', 'location', 'capacity', 'worker')
    list_filter = ('worker',)

 
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
    

 

 
@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('customer', 'order', 'rating', 'submitted_at')
    list_filter = ('rating', 'submitted_at')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "customer":
            kwargs["queryset"] = CustomUser.objects.filter(role='customer')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    

class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        
    def clean_price(self):
        price = self.cleaned_data['price']
        if price <= 0:
            raise ValidationError("Price must be greater than zero")
        return price


class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('name', 'product_type', 'price', 'description_short', 'image_tag')
    list_filter = ('product_type',)
    search_fields = ('name', 'product_type')
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return '-'
    image_tag.short_description = 'Image'



class StoreAdminForm(forms.ModelForm):
    class Meta:
        model = Store
        exclude = ('good_trays', 'good_loose', 'date_recorded')  # Add date_recorded here
        
    def clean(self):
        cleaned_data = super().clean()
        entry_type = cleaned_data.get('entry_type')
        product = cleaned_data.get('product')
        eggs_collection = cleaned_data.get('eggs_collection')
        
        if entry_type == 'egg' and not eggs_collection:
            raise ValidationError("Egg entries require an eggs collection reference")
            
        if entry_type == 'product' and not product:
            raise ValidationError("Product entries require a product selection")
            
        if entry_type == 'egg' and product:
            raise ValidationError("Egg entries shouldn't have a product association")
            
        return cleaned_data

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    form = StoreAdminForm
    list_display = ('entry_type', 'product_or_eggs', 'quantity_display', 'get_date_recorded')
    list_filter = ('entry_type',)
    readonly_fields = ('get_date_recorded', 'good_trays', 'good_loose', 'total_rejects')
    
    fieldsets = (
        ('General Information', {
            'fields': ('entry_type', 'quality_checker', 'notes')
        }),
        ('Egg-Specific', {
            'fields': ('eggs_collection', 'good_eggs', 'good_trays', 'good_loose',
                      'broken_eggs', 'cracked_eggs', 'dirty_eggs'),
            'classes': ('collapse',)
        }),
        ('Product-Specific', {
            'fields': ('product', 'unit', 'quantity'),
            'classes': ('collapse',)
        }),
    )

     # For number units, validate whole numbers
    def clean(self):
        cleaned_data = super().clean()
        entry_type = cleaned_data.get('entry_type')
        unit = cleaned_data.get('unit')
        quantity = cleaned_data.get('quantity')
        
        # For number units, validate whole numbers
        if unit == 'number' and quantity is not None:
            if quantity != quantity.to_integral_value():
                raise ValidationError({
                    'quantity': "Quantity must be a whole number when unit is 'Number'"
                })
    
    def get_date_recorded(self, obj):
        return obj.date_recorded
    get_date_recorded.short_description = 'Date Recorded'
    
    def product_or_eggs(self, obj):
        return obj.eggs_collection if obj.entry_type == 'egg' else obj.product
    product_or_eggs.short_description = 'Item'
    
    def quantity_display(self, obj):
        if obj.entry_type == 'egg':
            return f"{obj.good_eggs} eggs"
        return f"{obj.quantity} {obj.unit}"
    quantity_display.short_description = 'Quantity'


from decimal import Decimal

class SaleAdminForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['stock_manager'].queryset = self.fields['stock_manager'].queryset.filter(
            role='stock_manager'
        )
        
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        
        if product and quantity:
            try:
                if product.product_type == 'eggs':
                    available = Store.objects.filter(
                        entry_type='egg',
                        good_eggs__gt=0
                    ).aggregate(total=Sum('good_eggs'))['total'] or 0
                    if available < int(quantity):
                        raise ValidationError(
                            f"Insufficient eggs. Available: {available}, Requested: {int(quantity)}"
                        )
                else:
                    available = Store.objects.filter(
                        entry_type='product',
                        product=product,
                        quantity__gt=0
                    ).aggregate(total=Sum('quantity'))['total'] or 0
                    if available < float(quantity):
                        raise ValidationError(
                            f"Insufficient {product.name}. Available: {available}, Requested: {float(quantity)}"
                        )
            except Exception as e:
                raise ValidationError(str(e))
        
        return cleaned_data
    

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    form = SaleAdminForm
    list_display = ('product', 'quantity', 'sale_date', 'stock_manager', 'stock_deducted')
    list_filter = ('product__product_type', 'sale_date')
    readonly_fields = ('stock_deducted', 'sale_date')
    
    actions = ['cancel_sale_and_restock']
    
    def cancel_sale_and_restock(self, request, queryset):
        for sale in queryset:
            if sale.stock_deducted:
                try:
                    with transaction.atomic():
                        # Restock logic (you'll need to implement Store.restock_inventory)
                        Store.restock_inventory(sale.product, sale.quantity)
                        sale.stock_deducted = False
                        sale.delete()
                except Exception as e:
                    self.message_user(request, f"Error canceling sale {sale.id}: {str(e)}", level='error')
    cancel_sale_and_restock.short_description = "Cancel selected sales and restock inventory"

from decimal import Decimal

class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = self.fields['customer'].queryset.filter(
            role='customer'
        )
        
    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        product = self.cleaned_data.get('product')
        
        if product and product.product_type == 'eggs':
            # Proper way to check if Decimal is a whole number
            if quantity != quantity.to_integral_value():
                raise ValidationError("Egg quantity must be a whole number")
            return quantity.to_integral_value()
            
        return quantity
    

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    list_display = ('customer', 'product', 'status', 'order_date', 'stock_deducted')
    list_filter = ('status', 'product__product_type')
    readonly_fields = ('order_date', 'stock_deducted')
    actions = ['update_order_status']
    
    fieldsets = (
        (None, {
            'fields': ('customer', 'product', 'quantity', 'status')
        }),
        ('Dates', {
            'fields': ('order_date',),
            'classes': ('collapse',)
        }),
    )
    
    def update_order_status(self, request, queryset):
        status = request.POST.get('status')
        if status:
            for order in queryset:
                order.status = status
                order.save()
            self.message_user(request, f"Updated {queryset.count()} orders to {status}")
    update_order_status.short_description = "Update status of selected orders"
    
    def response_change(self, request, obj):
        if 'status' in request.POST:
            try:
                obj.save()
            except ValidationError as e:
                self.message_user(request, str(e), level='error')
                return super().response_change(request, obj)
        return super().response_change(request, obj)