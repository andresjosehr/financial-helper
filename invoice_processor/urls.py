"""
URLs para el módulo invoice_processor.
"""
from django.urls import path
from . import views

app_name = 'invoice_processor'

urlpatterns = [
    path('process/', views.process_invoice_from_n8n, name='process_invoice'),
]
