from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from products.views import get_products_by_categories

def home(request):
    return JsonResponse({
        'status': 'online',
        'message': 'Financial Helper API is running',
        'endpoints': {
            'admin': '/admin/',
            'image_processor_test': '/image-processor/test/',
            'process_invoice': '/api/process-invoice/',
            'products_by_categories': '/api/products/by-categories/',
        }
    })

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('image-processor/', include('image_processor.urls')),
    path('api/', include('image_processor.urls')),
    path('api/products/by-categories/', get_products_by_categories, name='products-by-categories'),
]
