from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Product, ProductBrand, ProductVariant


@require_http_methods(["GET"])
def get_products_by_categories(request):
    """
    Endpoint para obtener productos filtrados por categorías.

    Query params:
    - categories: Lista de nombres de categorías separadas por coma
      Ejemplo: ?categories=Bebidas,Lácteos,Carnes

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
    # Obtener parámetro de categorías
    categories_param = request.GET.get('categories', '')

    if not categories_param:
        return JsonResponse({
            'productos': []
        })

    # Parsear categorías
    categories = [cat.strip() for cat in categories_param.split(',') if cat.strip()]

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
