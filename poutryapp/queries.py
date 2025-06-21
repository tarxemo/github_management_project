import graphene
from .models import (
    User, ChickenHouse, EggCollection, EggInventory, EggSale,
    FoodType, FoodInventory, FoodPurchase, FoodDistribution,
    Medicine, MedicineInventory, MedicinePurchase, MedicineDistribution,
    ChickenDeathRecord
)
from .outputs import *
from django.db.models import Sum, Q, F
from datetime import date, timedelta
from graphql.error import GraphQLError
from django.utils import timezone

class Query(graphene.ObjectType):
    # ------------------- Authentication & User Queries -------------------
    users = graphene.List(UserOutput)

    def resolve_users(self, info):
        return User.objects.select_related('chicken_house').exclude(is_superuser = True)
    
    current_user = graphene.Field(UserOutput)
    
    def resolve_current_user(self, info):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        return user

    users = graphene.List(
        UserOutput,
        user_type=graphene.String(),
        chicken_house_id=graphene.ID()
    )
    
    def resolve_users(self, info, user_type=None, chicken_house_id=None):
        if not info.context.user.is_authenticated or info.context.user.user_type != 'ADMIN':
            raise GraphQLError("Only admin can view users")
        
        queryset = User.objects.exclude(is_superuser=True)
        
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        
        if chicken_house_id:
            queryset = queryset.filter(chicken_house_id=chicken_house_id)
        
        return queryset

    # ------------------- Chicken House Queries -------------------
    chicken_houses = graphene.List(
        ChickenHouseOutput,
        active_only=graphene.Boolean(default_value=True)
    )
    
    def resolve_chicken_houses(self, info, active_only=True):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        queryset = ChickenHouse.objects.all()
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        # Workers can only see their assigned chicken house
        if user.user_type == 'WORKER':
            queryset = queryset.filter(owner=user)
        
        return queryset

    chicken_house = graphene.Field(
        ChickenHouseOutput,
        id=graphene.ID(required=True)
    )
    
    def resolve_chicken_house(self, info, id):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        try:
            house = ChickenHouse.objects.get(pk=id)
            
            # Workers can only see their assigned chicken house
            if user.user_type == 'WORKER' and user.chicken_house != house:
                raise GraphQLError("You can only view your assigned chicken house")
            
            return house
        except ChickenHouse.DoesNotExist:
            raise GraphQLError("Chicken house not found")

    # ------------------- Egg Management Queries -------------------
    egg_inventory = graphene.Field(EggInventoryOutput)
    
    def resolve_egg_inventory(self, info):
        user = info.context.user
        if not user.is_authenticated or user.user_type not in ['ADMIN', 'STOCK_MANAGER']:
            raise GraphQLError("Only admin and stock managers can view egg inventory")
        
        inventory, _ = EggInventory.objects.get_or_create(pk=1)
        return inventory

    egg_collections = graphene.List(
        EggCollectionOutput,
        chicken_house_id=graphene.ID(),
        start_date=graphene.Date(),
        end_date=graphene.Date(),
        confirmed_only=graphene.Boolean(default_value=False)
    )
    
    def resolve_egg_collections(self, info, chicken_house_id=None, start_date=None, end_date=None, confirmed_only=False):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        queryset = EggCollection.objects.all()
        
        # Filter by chicken house
        if chicken_house_id:
            queryset = queryset.filter(chicken_house_id=chicken_house_id)
        
        # Workers can only see their own collections
        if user.user_type == 'WORKER':
            queryset = queryset.filter(worker=user)
        
        # Date range filtering
        if start_date:
            queryset = queryset.filter(date_collected__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_collected__lte=end_date)
        
        # Confirmation status
        if confirmed_only:
            queryset = queryset.filter(stock_manager_confirmed=True)
        
        return queryset.order_by('-date_collected')

    daily_egg_report = graphene.Field(
        DailyEggReportOutput,
        date=graphene.Date(),
        chicken_house_id=graphene.ID()
    )
    
    def resolve_daily_egg_report(self, info, date=None, chicken_house_id=None):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        report_date = date if date else timezone.now().date()
        
        # Base query
        queryset = EggCollection.objects.filter(date_collected=report_date)
        
        # Filter by chicken house if specified
        if chicken_house_id:
            queryset = queryset.filter(chicken_house_id=chicken_house_id)
        
        # Workers can only see their own data
        if user.user_type == 'WORKER':
            queryset = queryset.filter(worker=user)
        
        # Calculate totals
        total_eggs = queryset.aggregate(
            total=Sum(F('full_trays')*30 + F('loose_eggs'))
        )['total'] or 0
        
        total_rejected = queryset.aggregate(
            total=Sum('rejected_eggs')
        )['total'] or 0
        
        return DailyEggReportOutput(
            date=report_date,
            total_eggs=total_eggs,
            total_rejected=total_rejected,
            collections=queryset
        )

    egg_sales = graphene.List(
        EggSaleOutput,
        start_date=graphene.Date(),
        end_date=graphene.Date(),
        buyer_name=graphene.String()
    )
    
    def resolve_egg_sales(self, info, start_date=None, end_date=None, buyer_name=None):
        user = info.context.user
        if not user.is_authenticated or user.user_type not in ['ADMIN', 'STOCK_MANAGER', "SALES_MANAGER"]:
            raise GraphQLError("Only admin and stock managers can view sales records")
        
        queryset = EggSale.objects.all()
        
        if start_date:
            queryset = queryset.filter(date_sold__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_sold__lte=end_date)
        if buyer_name:
            queryset = queryset.filter(buyer_name__icontains=buyer_name)
        
        return queryset.order_by('-date_sold')

    # ------------------- Food Management Queries -------------------
    food_types = graphene.List(FoodTypeOutput)
    
    def resolve_food_types(self, info):
        return FoodType.objects.all()

    food_inventory = graphene.List(FoodInventoryOutput)
    
    def resolve_food_inventory(self, info):
        user = info.context.user
        if not user.is_authenticated or user.user_type not in ['ADMIN', 'STOCK_MANAGER']:
            raise GraphQLError("Only admin and stock managers can view food inventory")
        
        return FoodInventory.objects.all()

    food_purchases = graphene.List(
        FoodPurchaseOutput,
        food_type_id=graphene.ID(),
        start_date=graphene.Date(),
        end_date=graphene.Date()
    )
    
    def resolve_food_purchases(self, info, food_type_id=None, start_date=None, end_date=None):
        user = info.context.user
        if not user.is_authenticated or user.user_type not in ['ADMIN', 'STOCK_MANAGER']:
            raise GraphQLError("Only admin and stock managers can view purchase records")
        
        queryset = FoodPurchase.objects.all()
        
        if food_type_id:
            queryset = queryset.filter(food_type_id=food_type_id)
        if start_date:
            queryset = queryset.filter(purchase_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(purchase_date__lte=end_date)
        
        return queryset.order_by('-purchase_date')

    food_distributions = graphene.List(
        FoodDistributionOutput,
        chicken_house_id=graphene.ID(),
        food_type_id=graphene.ID(),
        start_date=graphene.Date(),
        end_date=graphene.Date(),
        confirmed_only=graphene.Boolean(default_value=False)
    )
    
    def resolve_food_distributions(self, info, chicken_house_id=None, food_type_id=None, start_date=None, end_date=None, confirmed_only=False):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        queryset = FoodDistribution.objects.all()
        
        if chicken_house_id:
            queryset = queryset.filter(chicken_house_id=chicken_house_id)
        if food_type_id:
            queryset = queryset.filter(food_type_id=food_type_id)
        if start_date:
            queryset = queryset.filter(date_distributed__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_distributed__lte=end_date)
        if confirmed_only:
            queryset = queryset.filter(worker_confirmed=True)
        
        # Workers can only see distributions to their chicken house
        if user.user_type == 'WORKER':
            queryset = queryset.filter(chicken_house__owner=user)
        
        return queryset.order_by('-date_distributed')

    # ------------------- Medicine Management Queries -------------------
    
    medicines = graphene.List(MedicineOutput)
    
    def resolve_medicines(self, info):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        return Medicine.objects.all()

    medicine_inventory = graphene.List(MedicineInventoryOutput)
    
    def resolve_medicine_inventory(self, info):
        user = info.context.user
        if not user.is_authenticated or user.user_type not in ['ADMIN', 'STOCK_MANAGER', 'DOCTOR', "WORKER"]:
            raise GraphQLError("Only admin, stock managers and doctors can view medicine inventory")
        if user.user_type == "WORKER":
            return []
        return MedicineInventory.objects.all()

    medicine_purchases = graphene.List(
        MedicinePurchaseOutput,
        medicine_id=graphene.ID(),
        expiring_soon=graphene.Boolean(default_value=False)
    )
    
    def resolve_medicine_purchases(self, info, medicine_id=None, expiring_soon=False):
        user = info.context.user
        if not user.is_authenticated or user.user_type not in ['ADMIN', 'STOCK_MANAGER', 'DOCTOR', "WORKER"]:
            raise GraphQLError("Only admin, stock managers and doctors can view medicine purchases")
        
        if user.user_type == "WORKER":
            return []
        
        queryset = MedicinePurchase.objects.all()
        
        if medicine_id:
            queryset = queryset.filter(medicine_id=medicine_id)
        
        if expiring_soon:
            threshold_date = date.today() + timedelta(days=30)
            queryset = queryset.filter(expiry_date__lte=threshold_date)
        
        return queryset.order_by('expiry_date')

    medicine_distributions = graphene.List(
        MedicineDistributionOutput,
        chicken_house_id=graphene.ID(),
        medicine_id=graphene.ID(),
        start_date=graphene.Date(),
        end_date=graphene.Date(),
        needs_confirmation=graphene.Boolean(default_value=False)
    )
    
    def resolve_medicine_distributions(self, info, chicken_house_id=None, medicine_id=None, start_date=None, end_date=None, needs_confirmation=False):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        queryset = MedicineDistribution.objects.all()
        
        if chicken_house_id:
            queryset = queryset.filter(chicken_house_id=chicken_house_id)
        if medicine_id:
            queryset = queryset.filter(medicine_id=medicine_id)
        if start_date:
            queryset = queryset.filter(date_distributed__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_distributed__lte=end_date)
        if user.user_type == 'DOCTOR':
            queryset = queryset
        elif user.user_type == 'WORKER':
            queryset = queryset.filter(received_by=user)
        
        # Workers can only see distributions to their chicken house
        if user.user_type == 'WORKER':
            queryset = queryset.filter(chicken_house__owner=user)
        
        # Doctors can only see distributions they made
        # if user.user_type == 'DOCTOR':
        #     queryset = queryset.filter(distributed_by=user)
        
        return queryset.order_by('-date_distributed')

    # ------------------- Health Management Queries -------------------
    chicken_death_records = graphene.List(
        ChickenDeathRecordOutput,
        chicken_house_id=graphene.ID(),
        start_date=graphene.Date(),
        end_date=graphene.Date(),
        needs_confirmation=graphene.Boolean(default_value=False)
    )
    
    def resolve_chicken_death_records(self, info, chicken_house_id=None, start_date=None, end_date=None, needs_confirmation=False):
        user = info.context.user
        if not user.is_authenticated:
            raise GraphQLError("Authentication required")
        
        queryset = ChickenDeathRecord.objects.all()
        
        if chicken_house_id:
            queryset = queryset.filter(chicken_house_id=chicken_house_id)
        if start_date:
            queryset = queryset.filter(date_recorded__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_recorded__lte=end_date)
        if needs_confirmation and user.user_type == 'DOCTOR':
            queryset = queryset.filter(confirmed_by__isnull=True)
        
        # Workers can only see records from their chicken house
        if user.user_type == 'WORKER':
            queryset = queryset.filter(chicken_house__owner=user)
        
        return queryset.order_by('-date_recorded')

    # ------------------- Business Analytics Queries -------------------
    chicken_house_performance = graphene.List(
        ChickenHousePerformanceOutput,
        period=graphene.String(default_value="month")  # "day", "week", "month", "year"
    )
    
    def resolve_chicken_house_performance(self, info, period):
        user = info.context.user
        if not user.is_authenticated or user.user_type not in ['ADMIN', 'STOCK_MANAGER']:
            raise GraphQLError("Only admin and stock managers can view performance reports")
        
        # Calculate date range based on period
        today = date.today()
        if period == "day":
            start_date = today
        elif period == "week":
            start_date = today - timedelta(days=7)
        elif period == "month":
            start_date = today - timedelta(days=30)
        elif period == "year":
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=30)  # Default to month
        
        houses = ChickenHouse.objects.filter(is_active=True)
        results = []
        
        for house in houses:
            # Egg production
            egg_collections = EggCollection.objects.filter(
                chicken_house=house,
                date_collected__gte=start_date,
                stock_manager_confirmed=True
            )
            total_eggs = egg_collections.aggregate(
                total=Sum(F('full_trays')*30 + F('loose_eggs'))
            )['total'] or 0
            
            # Mortality
            death_records = ChickenDeathRecord.objects.filter(
                chicken_house=house,
                date_recorded__gte=start_date,
                confirmed_by__isnull=False
            )
            total_deaths = death_records.aggregate(
                total=Sum('number_dead')
            )['total'] or 0
            print(f"total death : {total_deaths}")
            # Food consumption
            food_distributions = FoodDistribution.objects.filter(
                chicken_house=house,
                date_distributed__gte=start_date,
                worker_confirmed=True
            )
            total_food = food_distributions.aggregate(
                total=Sum('sacks_distributed')
            )['total'] or 0
            print(f"{total_food}")
            # Calculate performance metrics
            days_in_period = (today - start_date).days
            avg_eggs_per_day = total_eggs / days_in_period if days_in_period > 0 else 0
            
            mortality_rate = (total_deaths / house.capacity) * 100 if house.capacity > 0 else 0
            print(f"results {mortality_rate} {days_in_period} {avg_eggs_per_day} {total_food}")
            results.append(ChickenHousePerformanceOutput(
                chicken_house=house,
                total_eggs=total_eggs,
                avg_eggs_per_day=avg_eggs_per_day,
                mortality_rate=mortality_rate,
                food_consumption=Decimal(total_food * 50)  # Convert sacks to kg
            ))
        
        return results

    inventory_summary = graphene.Field(InventorySummaryOutput)
    
    def resolve_inventory_summary(self, info):
        user = info.context.user
        if not user.is_authenticated or user.user_type not in ['ADMIN', 'STOCK_MANAGER']:
            raise GraphQLError("Only admin and stock managers can view inventory summary")
        
        egg_inventory = EggInventory.objects.first()
        if not egg_inventory:
            egg_inventory = EggInventory.objects.create(total_eggs=0, rejected_eggs=0)
        
        return InventorySummaryOutput(
            total_eggs=egg_inventory.total_eggs,
            food_inventory=FoodInventory.objects.all(),
            medicine_inventory=MedicineInventory.objects.all()
        )
        
    alerts = graphene.List(AlertType)

    def resolve_alerts(self, info):
        alerts = []

        # 1. Food Inventory Check
        for item in FoodInventory.objects.all():
            if item.quantity_in_sacks <= 5:  # Set your own threshold
                alerts.append(AlertType(
                    type="food",
                    title="Low Food Inventory",
                    message=f"{item.food_type.name} is running low ({item.quantity_in_sacks} sacks left)"
                ))

        # 2. Medicine Expiry Check
        soon = timezone.now().date() + timedelta(days=7)
        expiring = Medicine.objects.filter(expiry_date__lte=soon)
        for med in expiring:
            days = (med.expiry_date - timezone.now().date()).days
            alerts.append(AlertType(
                type="medicine",
                title="Medicine Expiring",
                message=f"{med.name} expires in {days} day{'s' if days != 1 else ''}"
            ))

        # 3. House Maintenance Placeholder (You can add actual logic based on inspection records)
        dirty_houses = ChickenHouse.objects.filter(is_active=True).order_by('?')[:1]
        for house in dirty_houses:
            alerts.append(AlertType(
                type="maintenance",
                title="Maintenance Due",
                message=f"{house.name} needs cleaning inspection"
            ))

        return alerts
