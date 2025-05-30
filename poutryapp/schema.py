from ast import Store
import graphene
from graphql import GraphQLError

from poutryapp.decorators import role_required

from  .views import Mutation
from .models import ChickenHouse, EggsCollection, HealthRecord, Order, Feedback, CustomUser, Product, Sale,Store
from .outputs import (
    ChickenHouseType,
    EggsCollectionType,
    HealthRecordType,
    OrderType,
    FeedbackType,
    ProductType,
    SaleType,
    StoreType,
    UserType
)


class Query(graphene.ObjectType):

    all_chicken_houses = graphene.List(ChickenHouseType)
    chicken_house = graphene.Field(ChickenHouseType, id=graphene.ID(required=True))


    # all_eggs_collections = graphene.List(EggsCollectionType)
    eggs_collection = graphene.Field(EggsCollectionType, id=graphene.ID(required=True))

   
    all_health_records = graphene.List(HealthRecordType)
    health_record = graphene.Field(HealthRecordType, id=graphene.ID(required=True))
 
    all_feedbacks = graphene.List(FeedbackType)
    feedback = graphene.Field(FeedbackType, id=graphene.ID(required=True))


    all_workers = graphene.List(UserType)
    all_doctors = graphene.List(UserType)
    all_customers = graphene.List(UserType)
    all_stock_managers = graphene.List(UserType)

    me = graphene.Field(UserType)
 
    all_chicken_houses = graphene.List(ChickenHouseType)
    chicken_house = graphene.Field(ChickenHouseType, id=graphene.ID(required=True))


    all_eggs_collections = graphene.List(
        EggsCollectionType,
        worker_id=graphene.ID(required=False)  # Make it optional
    )
    

    all_users = graphene.List(UserType)

    # @role_required(['admin']) 
    def resolve_all_users(root, info):
        return CustomUser.objects.all()
    

    all_users_by_role = graphene.List(UserType, role=graphene.String())

    # @role_required(['admin']) 
    def resolve_all_users_by_role(root, info, role=None):
        if role:
            return CustomUser.objects.filter(role__iexact=role)
        return CustomUser.objects.all()
    
    # @role_required(['admin']) 
    def resolve_all_chicken_houses(root, info):
        return ChickenHouse.objects.select_related('worker').all()

    def resolve_chicken_house(root, info, id):
        try:
            return ChickenHouse.objects.select_related('worker').get(pk=id)
        except ChickenHouse.DoesNotExist:
            return None
 
 

    def resolve_me(self, info):
        user = info.context.user
        if user.is_anonymous:
            raise GraphQLError("Not logged in!")
        return user



    # @role_required(['admin']) 
    def resolve_all_chicken_houses(root, info):
        return ChickenHouse.objects.all()

    def resolve_chicken_house(root, info, id):
        return ChickenHouse.objects.get(pk=id)

    def resolve_all_workers(root, info):
        return CustomUser.objects.filter(role='worker')

    def resolve_all_doctors(root, info):
        return CustomUser.objects.filter(role='doctor')

    def resolve_all_customers(root, info):
        user = info.context.user
        if user.is_authenticated:
            print("Authenticated ###########################")
            print(user.email)
        return CustomUser.objects.filter(role='customer')

    def resolve_all_stock_managers(root, info):
        return CustomUser.objects.filter(role='stock_manager')
    
    # @role_required(['admin','worker']) 
    def resolve_all_eggs_collections(root, info):
        return EggsCollection.objects.all()

    def resolve_eggs_collection(root, info, id):
        return EggsCollection.objects.get(pk=id)

     
    def resolve_all_health_records(root, info):
        return HealthRecord.objects.all()

    def resolve_health_record(root, info, id):
        return HealthRecord.objects.get(pk=id)

 
    def resolve_all_feedbacks(root, info):
        return Feedback.objects.all()

    def resolve_feedback(root, info, id):
        return Feedback.objects.get(pk=id)
    

    all_stores = graphene.List(StoreType)
    store_by_id = graphene.Field(StoreType, id=graphene.ID(required=True))
    stores_by_product = graphene.List(StoreType, product_id=graphene.ID(required=True))
    
    # Sale Queries
    all_sales = graphene.List(SaleType)
    sales_by_product = graphene.List(SaleType, product_id=graphene.ID(required=True))
    
    # Order Queries
    all_orders = graphene.List(OrderType)
    orders_by_customer = graphene.List(OrderType, customer_id=graphene.ID(required=True))
    orders_by_status = graphene.List(OrderType, status=graphene.String(required=True))
    
    # Product Queries
    all_products = graphene.List(ProductType)
    products_by_type = graphene.List(ProductType, product_type=graphene.String(required=True))

    def resolve_all_stores(self, info):
        return Store.objects.all()
    
    def resolve_store_by_id(self, info, id):
        return Store.objects.get(pk=id)
    
    def resolve_stores_by_product(self, info, product_id):
        return Store.objects.filter(product_id=product_id)
    
    def resolve_all_sales(self, info):
        return Sale.objects.all()
    
    def resolve_sales_by_product(self, info, product_id):
        return Sale.objects.filter(product_id=product_id)
    
    def resolve_all_orders(self, info):
        return Order.objects.all()
    
    def resolve_orders_by_customer(self, info, customer_id):
        return Order.objects.filter(customer_id=customer_id)
    
    def resolve_orders_by_status(self, info, status):
        return Order.objects.filter(status=status)
    
    def resolve_all_products(self, info):
        return Product.objects.all()
    
    def resolve_products_by_type(self, info, product_type):
        return Product.objects.filter(product_type=product_type)


schema = graphene.Schema(query=Query, mutation=Mutation)
