from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import EventTariff, Event

def _recompute_event_available(event: Event):
    total = 0
    for et in event.event_tariffs.filter(is_active=True):
        rem = max((et.available_quantity or 0) - (et.sales_count or 0), 0)
        total += rem
    Event.objects.filter(pk=event.pk).update(available_tickets=total)

@receiver(post_save, sender=EventTariff)
def on_eventtariff_save(sender, instance, **kwargs):
    _recompute_event_available(instance.event)

@receiver(post_delete, sender=EventTariff)
def on_eventtariff_delete(sender, instance, **kwargs):
    _recompute_event_available(instance.event)
