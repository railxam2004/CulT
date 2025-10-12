# tickets/services.py
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from events.models import EventTariff
from cart.models import CartItem
from .models import Order, OrderItem, Ticket

def create_order_from_cart(user):
    items = list(CartItem.objects.select_related('event', 'event_tariff').filter(user=user))
    if not items:
        raise ValueError("Корзина пуста.")

    order = Order.objects.create(user=user, total_price=Decimal('0.00'), status=Order.Status.PENDING)

    total = Decimal('0.00')
    for ci in items:
        price = ci.event_tariff.price
        OrderItem.objects.create(
            order=order,
            event=ci.event,
            event_tariff=ci.event_tariff,
            quantity=ci.quantity,
            unit_price=price
        )
        total += price * ci.quantity

    order.total_price = total
    order.save(update_fields=['total_price'])
    return order


@transaction.atomic
def finalize_order_payment(order: Order, user):
    if order.user_id != user.id:
        raise PermissionError("Чужой заказ.")
    if order.status != Order.Status.PENDING:
        return order

    # 1) проверяем остатки под блокировкой
    for item in order.items.select_related('event_tariff'):
        et = EventTariff.objects.select_for_update().get(pk=item.event_tariff_id)
        remaining = (et.available_quantity or 0) - (et.sales_count or 0)
        if item.quantity > remaining:
            raise ValueError(f"Недостаточно квоты по тарифу {et.tariff.name} (осталось {remaining}).")

    # 2) списываем квоты и создаём билеты
    for item in order.items.select_related('event', 'event_tariff'):
        et = EventTariff.objects.select_for_update().get(pk=item.event_tariff_id)
        et.sales_count = (et.sales_count or 0) + item.quantity
        et.save(update_fields=['sales_count'])

        for _ in range(item.quantity):
            Ticket.objects.create(
                order=order,
                user=order.user,
                event=item.event,
                event_tariff=item.event_tariff,
                qr_hash=Ticket.make_qr_hash()
            )

    # 3) помечаем заказ оплаченным и чистим корзину
    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=['status', 'paid_at'])

    CartItem.objects.filter(user=order.user).delete()
    return order
