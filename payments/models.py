from django.db import models

class PaymentTransaction(models.Model):
    provider = models.CharField(max_length=20, default='yookassa', db_index=True)
    order = models.ForeignKey('tickets.Order', on_delete=models.CASCADE, related_name='payments')
    payment_id = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(max_length=32, db_index=True)  # pending/succeeded/canceled/...
    event = models.CharField(max_length=64, blank=True)      # имя события вебхука, если есть
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.provider}:{self.payment_id} -> {self.status}'