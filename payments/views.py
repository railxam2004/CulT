import base64
import json
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect
)
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from tickets.services import create_order_from_cart, finalize_order_payment
from tickets.models import Order
from .models import PaymentTransaction
from .services import create_yk_payment, get_yk_payment


@login_required
def yk_start(request):
    """
    Создаёт Order из корзины и стартует оплату в ЮKassa.
    Для демо можно вызывать GET — но в продакшене лучше POST (чтобы избежать дублей).
    """
    # 1) Создаём заказ из корзины
    order = create_order_from_cart(request.user)
    if order.total_price <= 0:
        # Заказ пустой/нулевой — отправим на success сразу
        return redirect('cart:checkout_success')

    # 2) Создаём платёж в ЮKassa
    payment = create_yk_payment(order, return_url=settings.YOO_KASSA_RETURN_URL)

    # 3) Сохраним в лог (и для демонстрации — в сессию)
    PaymentTransaction.objects.update_or_create(
        payment_id=payment.id,
        defaults={
            "order": order,
            "status": payment.status,
            "amount": Decimal(payment.amount.value or '0'),
            "payload": payment.json(),
        }
    )
    request.session['yk_payment_id'] = payment.id
    request.session['yk_order_id'] = order.id

    # 4) Редиректим пользователя на страницу оплаты ЮKassa
    return HttpResponseRedirect(payment.confirmation.confirmation_url)


@csrf_exempt
def yk_webhook(request):
    """
    Вебхук от ЮKassa (опционально для локальной демки).
    В продакшене лучше держать включенным и проверять Basic auth.
    """
    if request.method != 'POST':
        return HttpResponseBadRequest('POST only')

    # Проверка Basic Auth (если не отключили в настройках)
    if not settings.YOO_KASSA_SKIP_WEBHOOK_AUTH:
        expected = 'Basic ' + base64.b64encode(
            f"{settings.YOO_KASSA_SHOP_ID}:{settings.YOO_KASSA_SECRET_KEY}".encode('utf-8')
        ).decode('utf-8')
        got = request.META.get('HTTP_AUTHORIZATION', '')
        if got != expected:
            return HttpResponseForbidden('Invalid signature')

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('Bad JSON')

    event = payload.get('event', '')
    obj = payload.get('object', {}) or {}
    payment_id = obj.get('id')
    status = obj.get('status')
    metadata = obj.get('metadata') or {}
    order_id = metadata.get('order_id')

    if not payment_id:
        return HttpResponseBadRequest('No payment id')

    # Лог/идемпотентность
    pt, _ = PaymentTransaction.objects.update_or_create(
        payment_id=payment_id,
        defaults={
            "order_id": order_id or None,
            "status": status or '',
            "event": event or '',
            "amount": Decimal(obj.get('amount', {}).get('value') or '0'),
            "payload": payload,
        }
    )

    # Если платёж успешен — финализируем заказ (если ещё не финализирован)
    if status == 'succeeded' and order_id:
        try:
            order = Order.objects.select_related('user').get(id=order_id)
            if order.status != Order.Status.PAID:
                finalize_order_payment(order, order.user)
        except Order.DoesNotExist:
            pass

    return HttpResponse('OK')