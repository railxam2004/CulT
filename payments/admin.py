from django.contrib import admin
from .models import PaymentTransaction

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'provider', 'status', 'order', 'amount', 'created_at')
    search_fields = ('payment_id', 'order__id')
    list_filter = ('status', 'provider', 'created_at')