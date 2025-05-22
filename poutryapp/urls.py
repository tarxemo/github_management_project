from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet

from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt
from .schema import schema  # adjust the import path to your schema.py location



router = DefaultRouter()
router.register(r'products', ProductViewSet)
 


urlpatterns = [
    # GraphQL endpoint for all models except products (which have REST API)
    path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True, schema=schema))),
    path('api/', include(router.urls)),

]
