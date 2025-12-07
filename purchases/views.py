import json
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Purchase, PurchaseItem
from users.models import UserProfile


@login_required
def purchase_list(request):
    """Vista de listado de compras con filtros."""
    # Solo mostrar compras del usuario autenticado
    purchases = Purchase.objects.filter(user=request.user).select_related('establishment', 'user').prefetch_related('items').order_by('-purchase_date', '-purchase_time')

    # Filtro por búsqueda
    search = request.GET.get('search', '').strip()
    if search:
        purchases = purchases.filter(
            Q(establishment__name__icontains=search) |
            Q(notes__icontains=search)
        )

    # Filtro por fecha desde
    date_from = request.GET.get('from')
    if date_from:
        purchases = purchases.filter(purchase_date__gte=date_from)

    # Filtro por fecha hasta
    date_to = request.GET.get('to')
    if date_to:
        purchases = purchases.filter(purchase_date__lte=date_to)

    # Calcular totales
    totals = purchases.aggregate(
        total_ves=Sum('total_ves'),
        total_usd_bcv=Sum('total_usd_bcv'),
        total_usd_binance=Sum('total_usd_binance')
    )

    # Obtener el telegram_user del perfil del usuario
    profile = UserProfile.objects.filter(user=request.user).first()
    telegram_user = profile.telegram_user if profile else ''

    context = {
        'purchases': purchases,
        'total_count': purchases.count(),
        'total_ves': totals['total_ves'] or 0,
        'total_usd_bcv': totals['total_usd_bcv'] or 0,
        'total_usd_binance': totals['total_usd_binance'] or 0,
        'telegram_user': telegram_user,
    }

    return render(request, 'purchases/list.html', context)


@login_required
def purchase_detail(request, pk):
    """Vista de detalle de una compra."""
    # Solo permitir ver compras del usuario autenticado
    purchase = get_object_or_404(
        Purchase.objects.select_related('establishment', 'user').prefetch_related('items__product'),
        pk=pk,
        user=request.user
    )

    context = {
        'purchase': purchase,
    }

    return render(request, 'purchases/detail.html', context)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_purchase_total(request, pk):
    """API para actualizar el total VES de una compra y recalcular USD."""
    try:
        purchase = get_object_or_404(Purchase, pk=pk, user=request.user)
        data = json.loads(request.body)

        new_total_ves = data.get('total_ves')
        if new_total_ves is None:
            return JsonResponse({'success': False, 'error': 'total_ves es requerido'}, status=400)

        try:
            new_total_ves = Decimal(str(new_total_ves))
        except (InvalidOperation, ValueError):
            return JsonResponse({'success': False, 'error': 'total_ves debe ser un número válido'}, status=400)

        # Actualizar total VES
        purchase.total_ves = new_total_ves

        # Recalcular USD usando las tasas guardadas
        if purchase.bcv_rate and purchase.bcv_rate > 0:
            purchase.total_usd_bcv = new_total_ves / purchase.bcv_rate
        if purchase.binance_rate and purchase.binance_rate > 0:
            purchase.total_usd_binance = new_total_ves / purchase.binance_rate

        purchase.save()

        return JsonResponse({
            'success': True,
            'total_ves': float(purchase.total_ves),
            'total_usd_bcv': float(purchase.total_usd_bcv) if purchase.total_usd_bcv else None,
            'total_usd_binance': float(purchase.total_usd_binance) if purchase.total_usd_binance else None,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_purchase_item(request, pk, item_pk):
    """API para actualizar el total VES de un item y recalcular USD."""
    try:
        purchase = get_object_or_404(Purchase, pk=pk, user=request.user)
        item = get_object_or_404(PurchaseItem, pk=item_pk, purchase=purchase)
        data = json.loads(request.body)

        new_total_ves = data.get('total_ves')
        if new_total_ves is None:
            return JsonResponse({'success': False, 'error': 'total_ves es requerido'}, status=400)

        try:
            new_total_ves = Decimal(str(new_total_ves))
        except (InvalidOperation, ValueError):
            return JsonResponse({'success': False, 'error': 'total_ves debe ser un número válido'}, status=400)

        # Actualizar total VES del item
        item.total_ves = new_total_ves

        # Recalcular USD usando las tasas de la compra
        if purchase.bcv_rate and purchase.bcv_rate > 0:
            item.total_usd_bcv = new_total_ves / purchase.bcv_rate
        if purchase.binance_rate and purchase.binance_rate > 0:
            item.total_usd_binance = new_total_ves / purchase.binance_rate

        item.save()

        # Recalcular totales de la compra sumando todos los items
        items_total = purchase.items.aggregate(total=Sum('total_ves'))['total'] or Decimal('0')
        purchase.subtotal_ves = items_total
        purchase.total_ves = items_total + (purchase.tax_ves or Decimal('0'))

        if purchase.bcv_rate and purchase.bcv_rate > 0:
            purchase.total_usd_bcv = purchase.total_ves / purchase.bcv_rate
        if purchase.binance_rate and purchase.binance_rate > 0:
            purchase.total_usd_binance = purchase.total_ves / purchase.binance_rate

        purchase.save()

        return JsonResponse({
            'success': True,
            'item': {
                'id': str(item.id),
                'total_ves': float(item.total_ves),
                'total_usd_bcv': float(item.total_usd_bcv) if item.total_usd_bcv else None,
                'total_usd_binance': float(item.total_usd_binance) if item.total_usd_binance else None,
            },
            'purchase': {
                'subtotal_ves': float(purchase.subtotal_ves),
                'total_ves': float(purchase.total_ves),
                'total_usd_bcv': float(purchase.total_usd_bcv) if purchase.total_usd_bcv else None,
                'total_usd_binance': float(purchase.total_usd_binance) if purchase.total_usd_binance else None,
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_purchase(request, pk):
    """API para eliminar una compra y todos sus items."""
    try:
        purchase = get_object_or_404(Purchase, pk=pk, user=request.user)

        # Los items se eliminan automáticamente por CASCADE en el FK
        purchase.delete()

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_purchase_rates(request, pk):
    """API para actualizar las tasas de cambio y recalcular todos los USD."""
    try:
        purchase = get_object_or_404(Purchase, pk=pk, user=request.user)
        data = json.loads(request.body)

        bcv_rate = data.get('bcv_rate')
        binance_rate = data.get('binance_rate')

        # Validar que al menos una tasa fue enviada
        if bcv_rate is None and binance_rate is None:
            return JsonResponse({'success': False, 'error': 'Se requiere bcv_rate o binance_rate'}, status=400)

        # Actualizar tasa BCV si fue enviada
        if bcv_rate is not None:
            try:
                bcv_rate = Decimal(str(bcv_rate))
                if bcv_rate <= 0:
                    return JsonResponse({'success': False, 'error': 'bcv_rate debe ser mayor a 0'}, status=400)
                purchase.bcv_rate = bcv_rate
            except (InvalidOperation, ValueError):
                return JsonResponse({'success': False, 'error': 'bcv_rate debe ser un número válido'}, status=400)

        # Actualizar tasa Binance si fue enviada
        if binance_rate is not None:
            try:
                binance_rate = Decimal(str(binance_rate))
                if binance_rate <= 0:
                    return JsonResponse({'success': False, 'error': 'binance_rate debe ser mayor a 0'}, status=400)
                purchase.binance_rate = binance_rate
            except (InvalidOperation, ValueError):
                return JsonResponse({'success': False, 'error': 'binance_rate debe ser un número válido'}, status=400)

        # Recalcular USD de la compra
        if purchase.bcv_rate and purchase.bcv_rate > 0:
            purchase.total_usd_bcv = purchase.total_ves / purchase.bcv_rate
        if purchase.binance_rate and purchase.binance_rate > 0:
            purchase.total_usd_binance = purchase.total_ves / purchase.binance_rate

        purchase.save()

        # Recalcular USD de todos los items
        items_data = {}
        for item in purchase.items.all():
            if purchase.bcv_rate and purchase.bcv_rate > 0:
                item.total_usd_bcv = item.total_ves / purchase.bcv_rate
            if purchase.binance_rate and purchase.binance_rate > 0:
                item.total_usd_binance = item.total_ves / purchase.binance_rate
            item.save()

            items_data[str(item.id)] = {
                'total_ves': float(item.total_ves),
                'total_usd_bcv': float(item.total_usd_bcv) if item.total_usd_bcv else None,
                'total_usd_binance': float(item.total_usd_binance) if item.total_usd_binance else None,
            }

        return JsonResponse({
            'success': True,
            'purchase': {
                'bcv_rate': float(purchase.bcv_rate) if purchase.bcv_rate else None,
                'binance_rate': float(purchase.binance_rate) if purchase.binance_rate else None,
                'total_ves': float(purchase.total_ves),
                'total_usd_bcv': float(purchase.total_usd_bcv) if purchase.total_usd_bcv else None,
                'total_usd_binance': float(purchase.total_usd_binance) if purchase.total_usd_binance else None,
            },
            'items': items_data
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_telegram_user(request):
    """API para actualizar el telegram_user del perfil del usuario."""
    try:
        data = json.loads(request.body)
        telegram_user = data.get('telegram_user', '').strip()

        # Limpiar el @ si lo incluye
        if telegram_user.startswith('@'):
            telegram_user = telegram_user[1:]

        # Obtener o crear el perfil
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'telegram_user': telegram_user if telegram_user else None}
        )

        if not created:
            profile.telegram_user = telegram_user if telegram_user else None
            profile.save()

        return JsonResponse({
            'success': True,
            'telegram_user': profile.telegram_user or ''
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
