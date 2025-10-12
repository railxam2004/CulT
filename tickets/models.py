# tickets/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid

from events.models import Event, EventTariff

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает оплаты'
        PAID = 'paid', 'Оплачен'
        CANCELED = 'canceled', 'Отменён'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_provider = models.CharField(max_length=50, blank=True)
    payment_id = models.CharField(max_length=100, blank=True)
    receipt_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Order #{self.pk} ({self.get_status_display()})'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='order_items')
    event_tariff = models.ForeignKey(EventTariff, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    def total_price(self):
        return self.unit_price * self.quantity


class Ticket(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tickets')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets')
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='tickets')
    event_tariff = models.ForeignKey(EventTariff, on_delete=models.PROTECT, related_name='tickets')

    qr_hash = models.CharField(max_length=64, unique=True, db_index=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Ticket #{self.pk} for {self.event.title}'

    @staticmethod
    def make_qr_hash():
        return uuid.uuid4().hex
