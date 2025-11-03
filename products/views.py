from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import Product, ProductBrand, ProductVariant
import json


@csrf_exempt
@require_http_methods(["POST"])
def get_products_by_categories(request):
    """
    Endpoint para obtener productos filtrados por categorías.

    Body JSON:
    {
        "categories": ["Bebidas", "Lácteos", "Carnes"]
    }

    Returns:
    {
        "productos": [
            {
                "id": "uuid",
                "name": "Mantequilla",
                "brands": ["Mavesa", "Primor"],
                "category": "Lácteos",
                "variants": [
                    {"type": "size", "value": "200gm"},
                    {"type": "version", "value": "Light"}
                ]
            }
        ]
    }
    """
    try:
        # Parsear body JSON
        body = json.loads(request.body)
        categories = body.get('categories', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({
            'error': 'Body JSON inválido. Se espera: {"categories": ["Cat1", "Cat2"]}'
        }, status=400)

    if not categories or not isinstance(categories, list):
        return JsonResponse({
            'productos': []
        })

    # Limpiar y filtrar categorías vacías
    categories = [cat.strip() for cat in categories if cat and isinstance(cat, str) and cat.strip()]

    # Consultar productos filtrados por categorías
    products = Product.objects.filter(
        category__name__in=categories
    ).select_related('category').prefetch_related('brands', 'variants')

    # Serializar productos
    productos_data = []
    for product in products:
        variants_data = [
            {
                'type': variant.type,
                'value': variant.value
            }
            for variant in product.variants.all()
        ]

        brands_data = [brand.name for brand in product.brands.all()]

        productos_data.append({
            'id': str(product.id),
            'name': product.name,
            'brands': brands_data,
            'category': product.category.name if product.category else None,
            'variants': variants_data
        })

    return JsonResponse({
        'productos': productos_data
    })
