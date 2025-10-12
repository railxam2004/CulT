# cart/admin.py
from django.contrib import admin
from .models import CartItem

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'event_tariff', 'quantity', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('user__username', 'event__title', 'event_tariff__tariff__name')
