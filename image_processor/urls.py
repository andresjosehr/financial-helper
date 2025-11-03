from django.urls import path
from . import views

urlpatterns = [
    path('test/', views.test_page, name='image_processor_test'),
    path('tuning/', views.tuning_page, name='image_processor_tuning'),
    path('process-invoice/', views.process_invoice_optimal, name='process_invoice'),
    path('process-with-params/', views.process_with_params, name='process_with_params'),
]
