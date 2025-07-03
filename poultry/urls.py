"""
URL configuration for poultry project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from poultry.views import *
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt
# from django_graphql_playground.views import playground
from django.conf import settings

urlpatterns = [
    path('hidfor/', admin.site.urls),
    path('reports/', ReportAPIView.as_view(), name='reports-api'),
    path("gql/", csrf_exempt(GraphQLView.as_view(graphiql=settings.DEBUG))),
    path("profits/", ProfitabilityTrendReport.as_view()),
    path("costs/", CostOfProductionReport.as_view()),
    path("financials/", FinancialDashboardReport.as_view())
]

