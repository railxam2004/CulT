from django.conf import settings
from django.db import models
from events.models import Event, EventTariff

class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart_items')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='cart_items')
    event_tariff = models.ForeignKey(EventTariff, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'event_tariff')]
        ordering = ['-added_at']

    @property
    def unit_price(self):
        return self.event_tariff.price

    @property
    def subtotal(self):
        return self.event_tariff.price * self.quantity
