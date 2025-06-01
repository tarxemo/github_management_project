import graphene
from graphene import ObjectType, Field, List, Int, Float, String, DateTime
from graphene_django.filter import DjangoFilterConnectionField
from django.db.models import Sum, Count, F, Q, Avg, Max, Min, Func, Value, ExpressionWrapper, IntegerField
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay, Coalesce
from .models import *
from .outputs import *
from datetime import timedelta, datetime
from django.utils import timezone
from graphql import GraphQLError

class ChickenHousePerformanceType(ObjectType):
    house_name = String()
    total_chickens = Int()
    alive_chickens = Int()
    dead_chickens = Int()
    egg_production_rate = Float()  # Average eggs per chicken
    total_eggs_collected = Int()
    mortality_rate = Float()       # Dead chickens / total * 100
    food_consumption = Float()     # In kilograms or relevant unit
    vaccine_usage = Float()        # Could be total count or cost
    average_age = Float()          # Average chicken age in days
    occupancy_rate = Float() 

class SalesTrendsType(ObjectType):
    date = String()  # Could be day, week, or month depending on granularity
    total_sales = Int()  # Total transactions
    revenue = Float()  # Total revenue on that date
    egg_trays_sold = Int()
    egg_singles_sold = Int()
    chicken_units_sold = Int()
    avg_sale_value = Float()
    top_selling_item = String()
    cost_of_goods_sold = Float()
    profit = Float()

class BusinessMetrics(ObjectType):
    total_eggs_collected = Int()
    total_eggs_sold = Int()
    total_chickens = Int()
    total_alive_chickens = Int()
    total_revenue = Float()
    total_expenses = Float()
    net_profit = Float()
    food_costs = Float()
    vaccine_costs = Float()
    operational_costs = Float()
    avg_eggs_per_house = Float()
    avg_mortality_rate = Float()

    # Add these fields as resolvable types
    chicken_house_performance = List(ChickenHousePerformanceType)
    sales_trends = List(SalesTrendsType)
    expense_trends = List(SalesTrendsType)
    health_status = String()
    inventory_status = String()
    worker_performance = String()
    customer_purchase_history = String()


class ChickenHousePerformance(ObjectType):
    house = Field(ChickenHouseOutput)
    eggs_collected = Int()
    eggs_sold = Int()
    current_chickens = Int()
    mortality_rate = Float()
    avg_egg_production = Float()
    food_consumption = Float()
    revenue_generated = Float()

class SalesTrend(ObjectType):
    period = String()
    total_sales = Float()
    egg_sales = Float()
    chicken_sales = Float()
    other_sales = Float()

class ExpenseTrend(ObjectType):
    period = String()
    total_expenses = Float()
    food_expenses = Float()
    health_expenses = Float()
    operational_expenses = Float()

class HealthStatus(ObjectType):
    house = Field(ChickenHouseOutput)
    healthy_count = Int()
    sick_count = Int()
    vaccination_count = Int()
    mortality_count = Int()
    last_vaccination = DateTime()

class InventoryStatus(ObjectType):
    current_eggs = Int()
    full_trays = Int()
    remaining_eggs = Int()
    eggs_collected_today = Int()
    eggs_sold_today = Int()

class WorkerPerformance(ObjectType):
    worker = Field(UserOutput)
    houses_managed = Int()
    eggs_collected = Int()
    avg_egg_performance = Float()
    last_collection_date = DateTime()

class CustomerPurchaseHistory(ObjectType):
    customer = Field(UserOutput)
    total_purchases = Float()
    last_purchase_date = DateTime()
    favorite_product = String()
    purchase_frequency = Float()

class ComparativeAnalysis(ObjectType):
    best_performing_house = Field(ChickenHouseOutput)
    worst_performing_house = Field(ChickenHouseOutput)
    most_profitable_product = String()
    highest_expense_category = String()
    busiest_sales_period = String()
    egg_production_trend = List(SalesTrend)
    expense_trend = List(ExpenseTrend)

# Dashboard-specific types (simplified for brevity)
class SalesManagerDashboard(ObjectType):
    sales_summary = Field(BusinessMetrics)
    sales_trends = List(SalesTrend)
    top_customers = List(CustomerPurchaseHistory)
    inventory_status = Field(InventoryStatus)

class DoctorDashboard(ObjectType):
    health_status = List(HealthStatus)
    vaccination_records = List(VaccinationRecordOutput)
    mortality_rates = List(ChickenHousePerformance)

class WorkerDashboard(ObjectType):
    assigned_houses = List(ChickenHouseOutput)
    recent_collections = List(EggCollectionOutput)
    performance_metrics = Field(WorkerPerformance)

class CustomerDashboard(ObjectType):
    purchase_history = List(SaleOutput)
    favorite_products = List(String)
    spending_summary = Field(CustomerPurchaseHistory)

class Query(ObjectType):
    # Basic model queries
    # users = DjangoFilterConnectionField(UserOutput)
    # chicken_houses = DjangoFilterConnectionField(ChickenHouseOutput)
    # chickens = DjangoFilterConnectionField(ChickenOutput)
    # egg_collections = DjangoFilterConnectionField(EggCollectionOutput)
    # sales = DjangoFilterConnectionField(SaleOutput)
    # expenses = DjangoFilterConnectionField(ExpenseOutput)
    # health_reports = DjangoFilterConnectionField(HealthReportOutput)
    
    # Dashboard queries
    admin_dashboard = Field(BusinessMetrics)
    sales_manager_dashboard = Field(SalesManagerDashboard)
    doctor_dashboard = Field(DoctorDashboard)
    worker_dashboard = Field(WorkerDashboard, worker_id=ID())
    customer_dashboard = Field(CustomerDashboard, customer_id=ID())
    
    # Business analytics queries
    business_metrics = Field(BusinessMetrics, 
                           start_date=DateTime(), 
                           end_date=DateTime())
    
    chicken_house_performance = List(ChickenHousePerformance,
                                   time_frame=String())
    
    sales_trends = List(SalesTrend,
                       time_frame=String(),
                       period=String())
    
    expense_trends = List(ExpenseTrend,
                         time_frame=String(),
                         period=String())
    
    health_status_report = List(HealthStatus)
    
    inventory_status = Field(InventoryStatus)
    
    worker_performance = List(WorkerPerformance)
    
    customer_purchase_history = List(CustomerPurchaseHistory)
    
    comparative_analysis = Field(ComparativeAnalysis,
                               time_frame=String())
    


    def resolve_admin_dashboard(self, info):
        """Comprehensive dashboard for admin with all key metrics"""
        try:
            # Date ranges (not currently used but useful for future extensions)
            today = timezone.now().date()
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)

            # Eggs metrics
            total_eggs_collected = EggCollection.objects.aggregate(
                total=Coalesce(Sum('total_eggs'), 0)
            )['total']

            # Calculate eggs sold (egg trays * 30 + singles)
            total_eggs_sold_expr = ExpressionWrapper(
                F('egg_trays') * 30 + F('egg_singles'),
                output_field=IntegerField()
            )
            total_eggs_sold = SaleItem.objects.filter(
                sale__sale_type='EGG'
            ).aggregate(
                total=Coalesce(Sum(total_eggs_sold_expr), 0)
            )['total']

            # Chicken metrics
            total_chickens = Chicken.objects.count()
            total_alive_chickens = Chicken.objects.filter(is_alive=True).count()

            # Financial metrics
            total_revenue = Sale.objects.aggregate(
                total=Coalesce(Sum('total_amount'), 0)
            )['total']
            total_expenses = Expense.objects.aggregate(
                total=Coalesce(Sum('amount'), 0)
            )['total']
            net_profit = total_revenue - total_expenses

            # Cost breakdown
            food_costs = Expense.objects.filter(
                expense_type='FOOD'
            ).aggregate(total=Coalesce(Sum('amount'), 0))['total']
            vaccine_costs = Expense.objects.filter(
                expense_type='VACCINE'
            ).aggregate(total=Coalesce(Sum('amount'), 0))['total']
            operational_costs = Expense.objects.filter(
                expense_type__in=['EQUIPMENT', 'UTILITY', 'SALARY']
            ).aggregate(total=Coalesce(Sum('amount'), 0))['total']

            # Performance metrics
            avg_eggs_per_house = ChickenHouse.objects.annotate(
                egg_count=Coalesce(Sum('egg_collections__total_eggs'), 0)
            ).aggregate(
                avg=Coalesce(Avg('egg_count'), 0)
            )['avg']

            mortality_count = Chicken.objects.filter(is_alive=False).count()
            avg_mortality_rate = (mortality_count / total_chickens * 100) if total_chickens else 0

            return BusinessMetrics(
                total_eggs_collected=total_eggs_collected,
                total_eggs_sold=total_eggs_sold,
                total_chickens=total_chickens,
                total_alive_chickens=total_alive_chickens,
                total_revenue=total_revenue,
                total_expenses=total_expenses,
                net_profit=net_profit,
                food_costs=food_costs,
                vaccine_costs=vaccine_costs,
                operational_costs=operational_costs,
                avg_eggs_per_house=avg_eggs_per_house,
                avg_mortality_rate=avg_mortality_rate
            )
        except Exception as e:
            raise GraphQLError(f"Error generating admin dashboard: {str(e)}")

    
    def resolve_business_metrics(self, info, start_date=None, end_date=None):
        """Business metrics with date filtering"""
        try:
            # Create filters based on date range
            filters = {}
            if start_date:
                filters['date__gte'] = start_date
            if end_date:
                filters['date__lte'] = end_date
            
            # Apply date filters to relevant models
            egg_collections = EggCollection.objects.filter(**{
                'collection_date__gte': start_date,
                'collection_date__lte': end_date
            } if start_date and end_date else {})
            
            sales = Sale.objects.filter(**{
                'sale_date__gte': start_date,
                'sale_date__lte': end_date
            } if start_date and end_date else {})
            
            expenses = Expense.objects.filter(**{
                'date__gte': start_date,
                'date__lte': end_date
            } if start_date and end_date else {})
            
            # Calculate metrics
            total_eggs_collected = egg_collections.aggregate(
                total=Sum('total_eggs'))['total'] or 0
            
            sale_items = SaleItem.objects.filter(sale__in=sales)
            total_eggs_sold = sale_items.filter(
                sale__sale_type='EGG').aggregate(
                total=Sum(F('egg_trays')*30 + F('egg_singles')))['total'] or 0
            
            total_revenue = sales.aggregate(
                total=Sum('total_amount'))['total'] or 0
            total_expenses = expenses.aggregate(
                total=Sum('amount'))['total'] or 0
            net_profit = total_revenue - total_expenses
            
            # Cost breakdown
            food_costs = expenses.filter(
                expense_type='FOOD').aggregate(
                total=Sum('amount'))['total'] or 0
            vaccine_costs = expenses.filter(
                expense_type='VACCINE').aggregate(
                total=Sum('amount'))['total'] or 0
            operational_costs = expenses.filter(
                expense_type__in=['EQUIPMENT', 'UTILITY', 'SALARY']).aggregate(
                total=Sum('amount'))['total'] or 0
            
            return BusinessMetrics(
                total_eggs_collected=total_eggs_collected,
                total_eggs_sold=total_eggs_sold,
                total_chickens=0,  # Not date-filtered
                total_alive_chickens=0,  # Not date-filtered
                total_revenue=total_revenue,
                total_expenses=total_expenses,
                net_profit=net_profit,
                food_costs=food_costs,
                vaccine_costs=vaccine_costs,
                operational_costs=operational_costs,
                avg_eggs_per_house=0,  # Not implemented
                avg_mortality_rate=0  # Not implemented
            )
        except Exception as e:
            raise GraphQLError(f"Error generating business metrics: {str(e)}")
    
    def resolve_chicken_house_performance(self, info, time_frame='month'):
        """Performance metrics for all chicken houses"""
        try:
            # Determine time frame filter
            today = timezone.now().date()
            if time_frame == 'week':
                start_date = today - timedelta(days=7)
            elif time_frame == 'month':
                start_date = today - timedelta(days=30)
            elif time_frame == 'year':
                start_date = today - timedelta(days=365)
            else:
                start_date = None
            
            houses = ChickenHouse.objects.all()
            performance_data = []
            
            for house in houses:
                # Egg collections
                egg_filters = {'chicken_house': house}
                if start_date:
                    egg_filters['collection_date__gte'] = start_date
                
                eggs_collected = EggCollection.objects.filter(
                    **egg_filters).aggregate(
                    total=Sum('total_eggs'))['total'] or 0
                
                # Sales from this house's eggs
                eggs_sold = SaleItem.objects.filter(
                    sale__sale_type='EGG',
                    sale__sale_date__gte=start_date if start_date else None,
                    egg_collection__chicken_house=house
                ).aggregate(
                    total=Sum(F('egg_trays')*30 + F('egg_singles')))['total'] or 0
                
                # Current chickens
                current_chickens = house.current_chicken_count
                
                # Mortality rate
                total_chickens = Chicken.objects.filter(
                    chicken_house=house).count()
                dead_chickens = Chicken.objects.filter(
                    chicken_house=house, is_alive=False).count()
                mortality_rate = (dead_chickens / total_chickens * 100) if total_chickens else 0
                
                # Average egg production (per chicken)
                avg_egg_production = (eggs_collected / current_chickens) if current_chickens else 0
                
                # Food consumption
                food_consumption = FoodDistribution.objects.filter(
                    chicken_house=house,
                    distribution_date__gte=start_date if start_date else None
                ).aggregate(total=Sum('quantity'))['total'] or 0
                
                # Revenue generated
                revenue_generated = Sale.objects.filter(
                    items__egg_collection__chicken_house=house,
                    sale_date__gte=start_date if start_date else None
                ).aggregate(total=Sum('total_amount'))['total'] or 0
                
                performance_data.append(ChickenHousePerformance(
                    house=house,
                    eggs_collected=eggs_collected,
                    eggs_sold=eggs_sold,
                    current_chickens=current_chickens,
                    mortality_rate=mortality_rate,
                    avg_egg_production=avg_egg_production,
                    food_consumption=food_consumption,
                    revenue_generated=revenue_generated
                ))
            
            return performance_data
        except Exception as e:
            raise GraphQLError(f"Error generating chicken house performance: {str(e)}")
    
    def resolve_sales_trends(self, info, time_frame='month', period='weekly'):
        """Sales trends for visualization"""
        try:
            # Determine time frame
            today = timezone.now().date()
            if time_frame == 'week':
                start_date = today - timedelta(days=7)
                trunc_func = TruncDay
                period_name = 'day'
            elif time_frame == 'month':
                start_date = today - timedelta(days=30)
                trunc_func = TruncWeek
                period_name = 'week'
            elif time_frame == 'year':
                start_date = today - timedelta(days=365)
                trunc_func = TruncMonth
                period_name = 'month'
            else:
                start_date = None
                trunc_func = TruncMonth
                period_name = 'month'
            
            # Get base queryset
            sales = Sale.objects.filter(
                sale_date__gte=start_date) if start_date else Sale.objects.all()
            
            # Annotate with period
            sales_by_period = sales.annotate(
                period=trunc_func('sale_date')
            ).values('period').annotate(
                total_sales=Sum('total_amount'),
                egg_sales=Sum('items__egg_price_per_tray',
                              filter=Q(items__egg_trays__gt=0)),
                chicken_sales=Sum('items__chicken_price',
                                 filter=Q(items__chicken__isnull=False)),
                other_sales=Sum('items__unit_price',
                               filter=Q(items__item_description__isnull=False))
            ).order_by('period')
            
            # Convert to SalesTrend objects
            trends = []
            for period_data in sales_by_period:
                trends.append(SalesTrend(
                    period=period_data['period'].strftime(
                        '%Y-%m-%d' if period_name == 'day' else
                        '%Y-%m-%d (Week)' if period_name == 'week' else
                        '%Y-%m'
                    ),
                    total_sales=period_data['total_sales'] or 0,
                    egg_sales=period_data['egg_sales'] or 0,
                    chicken_sales=period_data['chicken_sales'] or 0,
                    other_sales=period_data['other_sales'] or 0
                ))
            
            return trends
        except Exception as e:
            raise GraphQLError(f"Error generating sales trends: {str(e)}")
    
    def resolve_expense_trends(self, info, time_frame='month', period='weekly'):
        """Expense trends for visualization"""
        try:
            # Similar to sales trends but for expenses
            today = timezone.now().date()
            if time_frame == 'week':
                start_date = today - timedelta(days=7)
                trunc_func = TruncDay
                period_name = 'day'
            elif time_frame == 'month':
                start_date = today - timedelta(days=30)
                trunc_func = TruncWeek
                period_name = 'week'
            elif time_frame == 'year':
                start_date = today - timedelta(days=365)
                trunc_func = TruncMonth
                period_name = 'month'
            else:
                start_date = None
                trunc_func = TruncMonth
                period_name = 'month'
            
            expenses = Expense.objects.filter(
                date__gte=start_date) if start_date else Expense.objects.all()
            
            expenses_by_period = expenses.annotate(
                period=trunc_func('date')
            ).values('period').annotate(
                total_expenses=Sum('amount'),
                food_expenses=Sum('amount', filter=Q(expense_type='FOOD')),
                health_expenses=Sum('amount', filter=Q(expense_type='VACCINE')),
                operational_expenses=Sum('amount', filter=Q(
                    expense_type__in=['EQUIPMENT', 'UTILITY', 'SALARY']))
            ).order_by('period')
            
            trends = []
            for period_data in expenses_by_period:
                trends.append(ExpenseTrend(
                    period=period_data['period'].strftime(
                        '%Y-%m-%d' if period_name == 'day' else
                        '%Y-%m-%d (Week)' if period_name == 'week' else
                        '%Y-%m'
                    ),
                    total_expenses=period_data['total_expenses'] or 0,
                    food_expenses=period_data['food_expenses'] or 0,
                    health_expenses=period_data['health_expenses'] or 0,
                    operational_expenses=period_data['operational_expenses'] or 0
                ))
            
            return trends
        except Exception as e:
            raise GraphQLError(f"Error generating expense trends: {str(e)}")
    
    def resolve_health_status_report(self, info):
        """Current health status of all chicken houses"""
        try:
            houses = ChickenHouse.objects.all()
            health_data = []
            
            for house in houses:
                # Get latest health report
                latest_report = HealthReport.objects.filter(
                    chicken_house=house).order_by('-report_date').first()
                
                if latest_report:
                    healthy_count = latest_report.healthy_count
                    sick_count = latest_report.sick_count
                else:
                    healthy_count = house.current_chicken_count
                    sick_count = 0
                
                # Vaccination count
                vaccination_count = VaccinationRecord.objects.filter(
                    chicken_house=house).count()
                
                # Mortality count
                mortality_count = Chicken.objects.filter(
                    chicken_house=house, is_alive=False).count()
                
                # Last vaccination
                last_vaccination = VaccinationRecord.objects.filter(
                    chicken_house=house).order_by('-date_administered').first()
                
                health_data.append(HealthStatus(
                    house=house,
                    healthy_count=healthy_count,
                    sick_count=sick_count,
                    vaccination_count=vaccination_count,
                    mortality_count=mortality_count,
                    last_vaccination=last_vaccination.date_administered if last_vaccination else None
                ))
            
            return health_data
        except Exception as e:
            raise GraphQLError(f"Error generating health status report: {str(e)}")
    
    def resolve_inventory_status(self, info):
        """Current inventory status"""
        try:
            inventory = Inventory.objects.first()
            if not inventory:
                inventory = Inventory.objects.create(egg_count=0)
            
            # Today's collections and sales
            today = timezone.now().date()
            eggs_collected_today = EggCollection.objects.filter(
                collection_date=today).aggregate(
                total=Sum('total_eggs'))['total'] or 0
            
            eggs_sold_today = SaleItem.objects.filter(
                sale__sale_type='EGG',
                sale__sale_date__date=today
            ).aggregate(total=Sum(F('egg_trays')*30 + F('egg_singles')))['total'] or 0
            
            return InventoryStatus(
                current_eggs=inventory.egg_count,
                full_trays=inventory.egg_count // 30,
                remaining_eggs=inventory.egg_count % 30,
                eggs_collected_today=eggs_collected_today,
                eggs_sold_today=eggs_sold_today
            )
        except Exception as e:
            raise GraphQLError(f"Error generating inventory status: {str(e)}")
    
    def resolve_worker_performance(self, info):
        """Performance metrics for all workers"""
        try:
            workers = User.objects.filter(user_type='WORKER')
            performance_data = []
            
            for worker in workers:
                # Houses managed
                houses_managed = worker.chickenhouse_set.count()
                
                # Eggs collected
                eggs_collected = EggCollection.objects.filter(
                    collected_by=worker).aggregate(
                    total=Sum('total_eggs'))['total'] or 0
                
                # Average egg performance (per house)
                avg_egg_performance = (eggs_collected / houses_managed) if houses_managed else 0
                
                # Last collection date
                last_collection = EggCollection.objects.filter(
                    collected_by=worker).order_by('-collection_date').first()
                
                performance_data.append(WorkerPerformance(
                    worker=worker,
                    houses_managed=houses_managed,
                    eggs_collected=eggs_collected,
                    avg_egg_performance=avg_egg_performance,
                    last_collection_date=last_collection.collection_date if last_collection else None
                ))
            
            return performance_data
        except Exception as e:
            raise GraphQLError(f"Error generating worker performance: {str(e)}")
    
    def resolve_customer_purchase_history(self, info):
        """Purchase history for all customers"""
        try:
            customers = User.objects.filter(user_type='CUSTOMER')
            purchase_data = []
            
            for customer in customers:
                # Total purchases
                total_purchases = Sale.objects.filter(
                    customer=customer).aggregate(
                    total=Sum('total_amount'))['total'] or 0
                
                # Last purchase date
                last_purchase = Sale.objects.filter(
                    customer=customer).order_by('-sale_date').first()
                
                # Favorite product
                favorite_product = SaleItem.objects.filter(
                    sale__customer=customer
                ).values('sale__sale_type').annotate(
                    count=Count('id')
                ).order_by('-count').first()
                
                # Purchase frequency (days between purchases)
                purchases = Sale.objects.filter(
                    customer=customer).order_by('sale_date')
                if purchases.count() > 1:
                    first_date = purchases.first().sale_date
                    last_date = purchases.last().sale_date
                    days_between = (last_date - first_date).days
                    purchase_frequency = days_between / purchases.count()
                else:
                    purchase_frequency = 0
                
                purchase_data.append(CustomerPurchaseHistory(
                    customer=customer,
                    total_purchases=total_purchases,
                    last_purchase_date=last_purchase.sale_date if last_purchase else None,
                    favorite_product=favorite_product['sale__sale_type'] if favorite_product else None,
                    purchase_frequency=purchase_frequency
                ))
            
            return purchase_data
        except Exception as e:
            raise GraphQLError(f"Error generating customer purchase history: {str(e)}")
    
    def resolve_comparative_analysis(self, info, time_frame='month'):
        """Comparative analysis of various metrics"""
        try:
            # Get time frame filter
            today = timezone.now().date()
            if time_frame == 'week':
                start_date = today - timedelta(days=7)
            elif time_frame == 'month':
                start_date = today - timedelta(days=30)
            elif time_frame == 'year':
                start_date = today - timedelta(days=365)
            else:
                start_date = None
            
            # Best and worst performing houses
            houses = ChickenHouse.objects.annotate(
                eggs_collected=Coalesce(Sum(
                    'egg_collections__total_eggs',
                    filter=Q(egg_collections__collection_date__gte=start_date) if start_date else Q()
                ), 0),
                revenue_generated=Coalesce(Sum(
                    'egg_collections__sale_items__sale__total_amount',
                    filter=Q(egg_collections__sale_items__sale__sale_date__gte=start_date) if start_date else Q()
                ), 0)
            ).order_by('-eggs_collected')
            
            best_house = houses.first()
            worst_house = houses.last()
            
            # Most profitable product
            sales = Sale.objects.filter(
                sale_date__gte=start_date) if start_date else Sale.objects.all()
            
            product_profit = sales.values('sale_type').annotate(
                total=Sum('total_amount')
            ).order_by('-total').first()
            
            # Highest expense category
            expenses = Expense.objects.filter(
                date__gte=start_date) if start_date else Expense.objects.all()
            
            expense_category = expenses.values('expense_type').annotate(
                total=Sum('amount')
            ).order_by('-total').first()
            
            # Busiest sales period (hour of day)
            busiest_period = sales.annotate(
                hour=Func(
                    F('sale_date'),
                    function='HOUR',
                    output_field=Int()
                )
            ).values('hour').annotate(
                count=Count('id')
            ).order_by('-count').first()
            
            busiest_period_str = (
                f"{busiest_period['hour']}:00-{busiest_period['hour']+1}:00" 
                if busiest_period else None
            )
            
            # Get trends for visualization
            egg_production_trend = self.resolve_sales_trends(info, time_frame)
            expense_trend = self.resolve_expense_trends(info, time_frame)
            
            return ComparativeAnalysis(
                best_performing_house=best_house,
                worst_performing_house=worst_house,
                most_profitable_product=product_profit['sale_type'] if product_profit else None,
                highest_expense_category=expense_category['expense_type'] if expense_category else None,
                busiest_sales_period=busiest_period_str,
                egg_production_trend=egg_production_trend,
                expense_trend=expense_trend
            )
        except Exception as e:
            raise GraphQLError(f"Error generating comparative analysis: {str(e)}")


    # Add resolvers for dashboard queries
    def resolve_sales_manager_dashboard(self, info):
        return SalesManagerDashboard(
            sales_summary=self.resolve_business_metrics(self, info),
            sales_trends=self.resolve_sales_trends(self, info, time_frame='month'),
            top_customers=self.resolve_customer_purchase_history(self, info)[:5],
            inventory_status=self.resolve_inventory_status(self, info)
        )

    def resolve_doctor_dashboard(self, info):
        return DoctorDashboard(
            health_status=self.resolve_health_status_report(self, info),
            vaccination_records=VaccinationRecord.objects.all().order_by('-date_administered')[:10],
            mortality_rates=self.resolve_chicken_house_performance(self, info)
        )

    def resolve_worker_dashboard(self, info, worker_id):
        worker = User.objects.get(pk=worker_id, user_type='WORKER')
        return WorkerDashboard(
            assigned_houses=worker.chickenhouse_set.all(),
            recent_collections=EggCollection.objects.filter(
                collected_by=worker).order_by('-collection_date')[:5],
            performance_metrics=next(
                (wp for wp in self.resolve_worker_performance(self, info) 
                if wp.worker.id == worker.id), 
                None)
        )

    def resolve_customer_dashboard(self, info, customer_id):
        customer = User.objects.get(pk=customer_id, user_type='CUSTOMER')
        purchases = Sale.objects.filter(customer=customer).order_by('-sale_date')
        
        # Get top 3 product types
        favorite_products = SaleItem.objects.filter(
            sale__customer=customer
        ).values('sale__sale_type').annotate(
            count=Count('id')
        ).order_by('-count')[:3]
        
        return CustomerDashboard(
            purchase_history=purchases[:10],
            favorite_products=[p['sale__sale_type'] for p in favorite_products],
            spending_summary=next(
                (cp for cp in self.resolve_customer_purchase_history(self, info) 
                if cp.customer.id == customer.id), 
                None)
        )