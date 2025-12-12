from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse, FileResponse
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.cache import cache_control
from products.views import get_products_by_categories
from exchange_rates.views import chart_view
from config.backup_views import download_database_backup

def api_status(request):
    return JsonResponse({
        'status': 'online',
        'message': 'Financial Helper API is running',
        'endpoints': {
            'admin': '/admin/',
            'image_processor_test': '/image-processor/test/',
            'process_invoice': '/api/process-invoice/',
            'invoice_processor': '/api/invoice-processor/process/',
            'products_by_categories': '/api/products/by-categories/',
            'database_backup': '/api/backup/download/',
        }
    })

@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
def service_worker(request):
    sw_path = settings.BASE_DIR / 'static' / 'pwa' / 'service-worker.js'
    return FileResponse(open(sw_path, 'rb'), content_type='application/javascript')

urlpatterns = [
    path('', chart_view, name='home'),
    path('service-worker.js', service_worker, name='service-worker'),
    path('api/status/', api_status, name='api_status'),
    path('admin/', admin.site.urls),
    path('image-processor/', include('image_processor.urls')),
    path('api/', include('image_processor.urls')),
    path('api/invoice-processor/', include('invoice_processor.urls')),
    path('api/products/by-categories/', get_products_by_categories, name='products-by-categories'),
    path('exchange-rates/', include('exchange_rates.urls')),
    path('api/exchange-rates/', include('exchange_rates.urls')),
    path('api/backup/download/', download_database_backup, name='backup-download'),
    path('purchases/', include('purchases.urls')),
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
