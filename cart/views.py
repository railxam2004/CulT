# cart/views.py
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from events.models import EventTariff
from .models import CartItem
from tickets.models import Order
from tickets.services import create_order_from_cart, finalize_order_payment

@login_required
def add_to_cart(request, event_tariff_id):
    if request.method != 'POST':
        return redirect('events:list')

    et = get_object_or_404(
        EventTariff.objects.select_related('event', 'tariff'),
        pk=event_tariff_id,
        is_active=True
    )
    # событие должно быть опубликовано и активно
    if not (et.event.is_active and et.event.status == et.event.Status.PUBLISHED):
        messages.error(request, "Нельзя добавить билеты для неопубликованного мероприятия.")
        return redirect('events:detail', et.event.slug)

    try:
        qty = int(request.POST.get('quantity', '1') or 1)
    except ValueError:
        qty = 1
    if qty < 1:
        qty = 1

    remaining = (et.available_quantity or 0) - (et.sales_count or 0)
    existing = CartItem.objects.filter(user=request.user, event_tariff=et).aggregate(s=models.Sum('quantity'))['s'] or 0
    if qty + existing > remaining:
        messages.error(request, f"Недостаточно билетов. Доступно: {max(remaining - existing, 0)}.")
        return redirect('events:detail', et.event.slug)

    item, created = CartItem.objects.get_or_create(
        user=request.user,
        event=et.event,
        event_tariff=et,
        defaults={'quantity': qty}
    )
    if not created:
        item.quantity += qty
        item.save(update_fields=['quantity'])

    messages.success(request, "Билет(ы) добавлены в корзину.")
    return redirect('cart:view')


@login_required
def cart_view(request):
    items = CartItem.objects.select_related('event', 'event_tariff', 'event_tariff__tariff').filter(user=request.user)
    total = sum((ci.event_tariff.price * ci.quantity for ci in items), Decimal('0.00'))
    return render(request, 'cart/cart.html', {'items': items, 'total': total})


@login_required
def cart_update(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, user=request.user)
    try:
        qty = int(request.POST.get('quantity', '1') or 1)
    except ValueError:
        qty = 1

    if qty <= 0:
        item.delete()
        messages.info(request, "Позиция удалена.")
        return redirect('cart:view')

    et = item.event_tariff
    remaining = (et.available_quantity or 0) - (et.sales_count or 0)
    if qty > remaining:
        messages.error(request, f"Доступно только {remaining} шт.")
        return redirect('cart:view')

    item.quantity = qty
    item.save(update_fields=['quantity'])
    messages.success(request, "Количество обновлено.")
    return redirect('cart:view')


@login_required
def cart_remove(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, user=request.user)
    item.delete()
    messages.info(request, "Позиция удалена из корзины.")
    return redirect('cart:view')


@login_required
def checkout(request):
    items = CartItem.objects.select_related('event', 'event_tariff').filter(user=request.user)
    if not items:
        messages.info(request, "Корзина пуста.")
        return redirect('cart:view')

    if request.method == 'POST':
        try:
            order = create_order_from_cart(request.user)
        except ValueError:
            messages.error(request, "Корзина пуста.")
            return redirect('cart:view')
        # показываем "эмулятор оплаты"
        return render(request, 'cart/checkout_pay.html', {'order': order})

    total = sum((ci.event_tariff.price * ci.quantity for ci in items), Decimal('0.00'))
    return render(request, 'cart/checkout.html', {'items': items, 'total': total})


@login_required
def checkout_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    try:
        finalize_order_payment(order, request.user)
    except Exception as e:
        messages.error(request, f"Не удалось завершить оплату: {e}")
        return redirect('cart:checkout')
    messages.success(request, "Оплата прошла успешно. Билеты готовы!")
    return redirect('tickets:my_tickets')


@login_required
def checkout_cancel(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if order.status == Order.Status.PENDING:
        order.status = Order.Status.CANCELED
        order.canceled_at = timezone.now()
        order.save(update_fields=['status', 'canceled_at'])
    messages.info(request, "Оплата отменена.")
    return redirect('cart:view')
