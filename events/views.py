# events/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from tickets.models import Ticket

from .forms import EventForm, EventTariffFormSet
from .models import Category, Event


def _require_organizer(request):
    if not (request.user.is_authenticated and request.user.is_organizer):
        messages.info(request, "Доступно только организаторам.")
        return False
    return True


def _event_has_active_tariff(event: Event) -> bool:
    # хотя бы один активный тариф с положительным остатком
    for et in event.event_tariffs.filter(is_active=True):
        rem = max((et.available_quantity or 0) - (et.sales_count or 0), 0)
        if rem > 0:
            return True
    return False


# ---------- ПУБЛИЧНАЯ ВИТРИНА ----------

def event_list(request, slug=None):
    qs = Event.objects.filter(
        status=Event.Status.PUBLISHED,
        is_active=True
    ).select_related("category", "organizer").order_by("-starts_at")

    current_category = None
    if slug:
        current_category = get_object_or_404(Category, slug=slug)
        qs = qs.filter(category=current_category)

    paginator = Paginator(qs, 12)
    page = request.GET.get("page")
    events_page = paginator.get_page(page)

    categories = Category.objects.order_by("name")
    return render(request, "events/list.html", {
        "events": events_page,
        "categories": categories,
        "current_category": current_category,
    })


def event_detail(request, slug: str):
    event = get_object_or_404(
        Event,
        slug=slug,
        status=Event.Status.PUBLISHED,
        is_active=True
    )
    # считаем просмотр
    Event.objects.filter(pk=event.pk).update(views_count=F("views_count") + 1)
    event.refresh_from_db(fields=["views_count"])

    tariffs = event.event_tariffs.filter(is_active=True).select_related("tariff")
    return render(request, "events/detail.html", {"event": event, "tariffs": tariffs})


# ---------- КАБИНЕТ ОРГАНИЗАТОРА ----------

@login_required
def my_events(request):
    if not _require_organizer(request):
        return redirect("users:profile")

    qs = Event.objects.filter(organizer=request.user).order_by("-created_at")
    return render(request, "events/my_list.html", {"events": qs})


@login_required
def my_event_create(request):
    if not _require_organizer(request):
        return redirect("users:profile")

    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(organizer=request.user, commit=True)
            formset = EventTariffFormSet(request.POST, instance=event)
            if formset.is_valid():
                formset.save()

                if "submit_for_moderation" in request.POST:
                    if _event_has_active_tariff(event):
                        event.status = Event.Status.PENDING
                        event.save(update_fields=["status"])
                        messages.success(request, "Событие отправлено на модерацию.")
                    else:
                        messages.warning(
                            request,
                            "Нельзя отправить на модерацию без активных тарифов с положительным остатком. "
                            "Сохранено как черновик."
                        )
                else:
                    messages.success(request, "Черновик события сохранён.")
                return redirect("events:my_list")
            else:
                # Покажем ошибки формсета не теряя созданный черновик
                messages.error(request, "Проверьте тарифы: есть ошибки в форме.")
    else:
        form = EventForm()
        formset = EventTariffFormSet()

    # В GET при создании у формсета нет instance — создадим пустой
    if request.method != "POST":
        formset = EventTariffFormSet()

    return render(request, "events/form.html", {
        "form": form,
        "formset": formset,
        "is_edit": False,
    })


@login_required
def my_event_edit(request, pk: int):
    if not _require_organizer(request):
        return redirect("users:profile")

    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event)
        formset = EventTariffFormSet(request.POST, instance=event)
        if form.is_valid() and formset.is_valid():
            event = form.save(organizer=request.user, commit=True)
            formset.save()

            if "submit_for_moderation" in request.POST:
                if event.status in (Event.Status.DRAFT, Event.Status.REJECTED):
                    if _event_has_active_tariff(event):
                        event.status = Event.Status.PENDING
                        event.save(update_fields=["status"])
                        messages.success(request, "Событие отправлено на модерацию.")
                    else:
                        messages.warning(
                            request,
                            "Нельзя отправить на модерацию без активных тарифов с положительным остатком."
                        )
                else:
                    messages.info(request, "Событие уже на модерации или опубликовано.")
            else:
                messages.success(request, "Изменения сохранены.")
            return redirect("events:my_list")
    else:
        form = EventForm(instance=event)
        formset = EventTariffFormSet(instance=event)

    return render(request, "events/form.html", {
        "form": form,
        "formset": formset,
        "is_edit": True,
        "event": event,
    })

@login_required
def my_event_tickets(request, pk: int):
    if not _require_organizer(request):
        return redirect("users:profile")
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    tickets = (Ticket.objects
               .select_related('user', 'event_tariff', 'event_tariff__tariff')
               .filter(event=event)
               .order_by('-created_at'))
    return render(request, 'events/my_event_tickets.html', {'event': event, 'tickets': tickets})