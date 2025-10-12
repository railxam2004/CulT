from django.contrib import admin
from .models import Order, OrderItem, Ticket

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('unit_price',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_price', 'created_at', 'paid_at')
    list_filter = ('status', 'created_at', 'paid_at')
    search_fields = ('user__username', 'user__email')
    inlines = [OrderItemInline]

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'event', 'event_tariff', 'is_used', 'created_at')
    list_filter = ('is_used', 'event')
    search_fields = ('qr_hash', 'user__username', 'user__email', 'event__title')
