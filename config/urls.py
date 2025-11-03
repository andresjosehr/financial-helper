from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def home(request):
    return JsonResponse({
        'status': 'online',
        'message': 'Financial Helper API is running',
        'endpoints': {
            'admin': '/admin/',
            'image_processor_test': '/image-processor/test/',
            'process_invoice': '/api/process-invoice/',
        }
    })

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('image-processor/', include('image_processor.urls')),
    path('api/', include('image_processor.urls')),
]
