# events/admin.py
from django.contrib import admin
from .models import Category, Tariff, Event, EventTariff

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class EventTariffInline(admin.TabularInline):
    model = EventTariff
    extra = 0
    fields = ('tariff', 'price', 'available_quantity', 'sales_count', 'is_active')
    readonly_fields = ('sales_count',)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'organizer', 'starts_at', 'status', 'available_tickets', 'is_active')
    list_filter = ('status', 'category', 'is_active')
    search_fields = ('title', 'description', 'location')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [EventTariffInline]
