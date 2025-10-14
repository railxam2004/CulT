# tickets/services.py
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from events.models import EventTariff
from cart.models import CartItem
from .models import Order, OrderItem, Ticket
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
import logging

from .models import Order
from .utils import build_ticket_pdf
logger = logging.getLogger('mail')

def send_tickets_email(order_id: int, attach_pdfs: bool = True) -> None:
    """
    Отправляет пользователю письмо с билетами (PDF).
    Ошибки логируются и не пробрасываются наружу.
    """
    try:
        order = (Order.objects
                 .select_related('user')
                 .prefetch_related('tickets__event', 'tickets__event_tariff__tariff')
                 .get(pk=order_id))
    except Order.DoesNotExist:
        logger.error("send_tickets_email: order %s does not exist", order_id)
        return

    subject = f"{settings.SITE_NAME}: ваши билеты — заказ №{order.id}"
    ctx = {'order': order, 'site_name': settings.SITE_NAME, 'site_url': settings.SITE_URL}
    text = render_to_string('email/tickets_paid.txt', ctx)
    html = render_to_string('email/tickets_paid.html', ctx)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.user.email] if order.user and order.user.email else [],
    )
    if html:
        msg.attach_alternative(html, 'text/html')

    # Прикладываем PDF каждого билета
    if attach_pdfs:
        for t in order.tickets.all():
            try:
                pdf_bytes = build_ticket_pdf(t)  # должен вернуть bytes
                msg.attach(f"ticket-{t.id}.pdf", pdf_bytes, 'application/pdf')
            except Exception as e:
                logger.exception("PDF build failed for ticket %s (order %s): %s", t.id, order.id, e)

    # Отправка
    try:
        sent_count = msg.send(fail_silently=False)  # хотим поймать исключение
        logger.info("Tickets email sent: order=%s to=%s result=%s",
                    order.id, order.user.email, sent_count)
    except Exception as e:
        # не роняем оплату
        logger.exception("Tickets email FAILED: order=%s to=%s: %s",
                         order.id, order.user.email, e)

def create_order_from_cart(user):
    items = list(CartItem.objects.select_related('event', 'event_tariff').filter(user=user))
    if not items:
        raise ValueError("Корзина пуста.")

    # Запретим оформление, если в корзине есть прошедшие/закрытые события
    for ci in items:
        if not ci.event.is_buyable:
            raise ValueError(f"Нельзя оформить заказ: событие «{ci.event.title}» недоступно для покупки.")

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
    transaction.on_commit(lambda: send_tickets_email(order.id, attach_pdfs=True))
    return order

