import datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, F, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncDate
from django.shortcuts import render

from events.models import Event, EventTariff
from tickets.models import OrderItem, Ticket


@login_required
def dashboard_index(request):
    user = request.user
    is_admin = user.is_staff or user.is_superuser

    # --- Список событий в области видимости пользователя ---
    events_filter = Q()
    if not is_admin:
        events_filter &= Q(organizer=user)

    events_qs = (Event.objects
                 .filter(events_filter)
                 .select_related('category', 'organizer'))

    # --- Продажи (берём только оплаченные позиции заказа) ---
    items_qs = OrderItem.objects.filter(order__paid_at__isnull=False)
    if not is_admin:
        items_qs = items_qs.filter(event__organizer=user)

    line_total = ExpressionWrapper(
        F('unit_price') * F('quantity'),
        output_field=DecimalField(max_digits=14, decimal_places=2)
    )

    agg = items_qs.aggregate(
        revenue=Sum(line_total),
        sold=Sum('quantity')
    )
    revenue_total = agg['revenue'] or Decimal('0')
    sold_total = agg['sold'] or 0

    # --- Остатки по тарифам ---
    tariff_qs = EventTariff.objects.filter(event__in=events_qs)
    remaining_expr = ExpressionWrapper(
        F('available_quantity') - F('sales_count'),
        output_field=DecimalField(max_digits=12, decimal_places=0)
    )
    remaining_total = tariff_qs.aggregate(rem=Sum(remaining_expr))['rem'] or 0
    try:
        remaining_total = int(remaining_total)
    except Exception:
        remaining_total = 0

    # --- Посещаемость (помеченные билеты) ---
    tickets_used_qs = Ticket.objects.filter(is_used=True)
    if not is_admin:
        tickets_used_qs = tickets_used_qs.filter(event__organizer=user)
    checkins_total = tickets_used_qs.count()

    # --- Временной ряд (последние 30 дней) ---
    from django.utils import timezone
    today = timezone.localdate()
    start_date = today - datetime.timedelta(days=29)

    ts_qs = (items_qs
        .filter(order__paid_at__date__gte=start_date, order__paid_at__date__lte=today)
        .annotate(d=TruncDate('order__paid_at'))
        .values('d')
        .annotate(revenue=Sum(line_total), sold=Sum('quantity'))
        .order_by('d'))

    by_date = {row['d']: row for row in ts_qs}
    ts_labels = []
    ts_revenue = []
    ts_sold = []
    for i in range(30):
        d = start_date + datetime.timedelta(days=i)
        ts_labels.append(d.strftime('%d.%m'))
        row = by_date.get(d)
        ts_revenue.append(float(row['revenue']) if row and row['revenue'] else 0.0)
        ts_sold.append(int(row['sold']) if row and row['sold'] else 0)

    # --- Топ категорий по выручке ---
    cat_qs = (items_qs
              .values('event__category__name')
              .annotate(revenue=Sum(line_total))
              .order_by('-revenue')[:8])
    cat_labels = [row['event__category__name'] or 'Без категории' for row in cat_qs]
    cat_values = [float(row['revenue'] or 0) for row in cat_qs]

    # --- Топ событий по выручке ---
    top_events = (items_qs
                  .values('event__id', 'event__title', 'event__slug')
                  .annotate(revenue=Sum(line_total), sold=Sum('quantity'))
                  .order_by('-revenue')[:10])

    # --- Сводка по событиям (продано/остаток) ---
    sold_per_event = dict(
        items_qs.values('event__id').annotate(sold=Sum('quantity')).values_list('event__id', 'sold')
    )
    remaining_per_event = dict(
        tariff_qs.values('event_id').annotate(rem=Sum(remaining_expr)).values_list('event_id', 'rem')
    )

    events_summary = []
    for e in events_qs.order_by('-starts_at')[:50]:
        sold = int(sold_per_event.get(e.id, 0) or 0)
        rem = int(remaining_per_event.get(e.id, 0) or 0)
        if rem < 0:
            rem = 0
        events_summary.append({
            'id': e.id,
            'title': e.title,
            'slug': e.slug,
            'category': e.category.name if e.category else '',
            'starts_at': e.starts_at,
            'location': e.location,
            'sold': sold,
            'remaining': rem,
        })

    ctx = {
        'is_admin': is_admin,
        'cards': {
            'revenue_total': revenue_total,
            'sold_total': sold_total,
            'remaining_total': remaining_total,
            'checkins_total': checkins_total,
        },
        'ts_labels': ts_labels,
        'ts_revenue': ts_revenue,
        'ts_sold': ts_sold,
        'cat_labels': cat_labels,
        'cat_values': cat_values,
        'top_events': top_events,
        'events_summary': events_summary,
    }
    return render(request, "dashboard/index.html", ctx)
