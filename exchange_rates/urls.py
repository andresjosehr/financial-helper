from django.urls import path
from . import views

app_name = 'exchange_rates'

urlpatterns = [
    path('chart/', views.chart_view, name='chart'),
    path('bcv/', views.api_bcv_rates, name='api_bcv_rates'),
]
