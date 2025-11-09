from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Min, Case, When, Value, IntegerField, F
from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404, redirect, render
from tickets.models import Ticket
from favorites.models import Favorite
import csv
from django.http import HttpResponse
from django.utils import timezone
from .forms import EventForm, EventTariffFormSet, EventEditRequestForm
from .models import Category, Event, EventEditRequest
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .services.ai import generate_event_description, YandexGPTError



def _require_organizer(request):
    """
    Проверяет, является ли текущий пользователь авторизованным организатором.
    Отправляет сообщение, если условие не выполнено.
    """
    if not (request.user.is_authenticated and request.user.is_organizer):
        messages.info(request, "Доступно только организаторам.")
        return False
    return True


def _event_has_active_tariff(event: Event) -> bool:
    """
    Проверяет, есть ли у мероприятия хотя бы один активный тариф
    с ненулевым остатком билетов.
    """
    for et in event.event_tariffs.filter(is_active=True):
        rem = max((et.available_quantity or 0) - (et.sales_count or 0), 0)
        if rem > 0:
            return True
    return False



def event_list(request, slug=None):
    """
    Отображает список мероприятий с возможностью фильтрации, поиска и сортировки.
    """
    # Базовый queryset: только опубликованные и активные
    qs = (Event.objects
          .filter(status=Event.Status.PUBLISHED, is_active=True)
          .select_related('category', 'organizer')
          .prefetch_related('event_tariffs__tariff'))
    now = timezone.now()
    show_past = (request.GET.get('past') == '1')

    # Разделяем предстоящие и прошедшие
    if show_past:
        qs = qs.filter(starts_at__lt=now)
    else:
        qs = qs.filter(starts_at__gte=now)

    categories = Category.objects.all().order_by('name')

    # Параметры GET
    q = (request.GET.get('q') or '').strip()
    category_slug = (request.GET.get('category') or '').strip()
    city = (request.GET.get('city') or request.GET.get('location') or '').strip()
    date_from = request.GET.get('date_from') or ''
    date_to = request.GET.get('date_to') or ''
    sort = (request.GET.get('sort') or 'soon').strip()

    # Фильтры
    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    if city:
        qs = qs.filter(location__icontains=city)

    if date_from:
        df = parse_date(date_from)
        if df:
            qs = qs.filter(starts_at__date__gte=df)

    if date_to:
        dt = parse_date(date_to)
        if dt:
            qs = qs.filter(starts_at__date__lte=dt)

    # Поиск: приоритет "сначала по названию", затем "по словам из описания"
    # Разбиваем запрос на слова и строим OR-условия
    rank_applied = False
    if q:
        words = [w for w in q.replace(',', ' ').split() if w]
        q_title = Q()
        q_desc = Q()
        for w in words:
            q_title |= Q(title__icontains=w)
            q_desc |= Q(description__icontains=w)

        # Фильтруем по совпадению в названии ИЛИ описании
        qs = qs.filter(q_title | q_desc)

        # Ранжируем: 0 — попало по названию, 1 — только по описанию
        qs = qs.annotate(
            _rank=Case(
                When(q_title, then=Value(0)),
                When(q_desc, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        rank_applied = True

    # Сортировки
    # cheap -> по минимальной цене тарифа; popular -> по просмотрам; soon -> по дате начала
    if sort == 'cheap':
        qs = qs.annotate(min_price=Min('event_tariffs__price'))
        primary_order = 'min_price'
    elif sort == 'popular':
        primary_order = '-views_count'
    else:
        sort = 'soon'
        primary_order = 'starts_at'

    # Если есть поиск — сначала ранг, затем заданная сортировка
    if rank_applied:
        qs = qs.order_by('_rank', primary_order, 'id')
    else:
        qs = qs.order_by(primary_order, 'id')

    # Пагинация
    paginator = Paginator(qs, 12)
    page = request.GET.get('page')
    events_page = paginator.get_page(page)

    # Избранное: ID событий на текущей странице
    favorite_ids = set()
    if request.user.is_authenticated:
        ids_on_page = [e.id for e in events_page.object_list]
        favorite_ids = set(
            Favorite.objects
                    .filter(user=request.user, event_id__in=ids_on_page)
                    .values_list('event_id', flat=True)
        )

    # Базовая строка запроса без page для ссылок пагинации
    params = request.GET.copy()
    params.pop('page', None)
    base_qs = params.urlencode()

    ctx = {
        'events': events_page,
        'categories': categories,
        'current_category': category_slug,
        'q': q,
        'city': city,
        'date_from': date_from,
        'date_to': date_to,
        'sort': sort,
        'favorite_ids': favorite_ids,
        'base_qs': base_qs,
    }
    return render(request, 'events/list.html', ctx)


def event_detail(request, slug: str):
    """
    Отображает детальную страницу мероприятия.
    """
    event = get_object_or_404(
        Event,
        slug=slug,
        status=Event.Status.PUBLISHED,
        is_active=True
    )
    # считаем просмотр
    Event.objects.filter(pk=event.pk).update(views_count=F("views_count") + 1)
    event.refresh_from_db(fields=["views_count"])

    # Флаг избранного
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, event=event).exists()

    tariffs = event.event_tariffs.filter(is_active=True).select_related("tariff")
    return render(request, "events/detail.html", {
        "event": event,
        "tariffs": tariffs,
        "is_favorited": is_favorited,
    })


# ---------- КАБИНЕТ ОРГАНИЗАТОРА ----------

@login_required
# список моих мероприятий
def my_events(request):
    qs = (Event.objects
          .filter(organizer=request.user)
          .select_related('category')
          .prefetch_related('edit_requests'))

    # добавляем флаг наличия активной заявки
    for e in qs:
        e.has_pending_edit = e.edit_requests.filter(status='pending').exists()

    return render(request, "events/my_events.html", {"events": qs})


@login_required
#Создание нового мероприятия организатором
def my_event_create(request):
# Проверка, является ли пользователь организатором
    if not _require_organizer(request):
        return redirect("users:profile")

    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)
        # Инициализируем формсет для тарифов
        formset = EventTariffFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # Сохраняем событие (organizer передается в кастомном save формы)
            event = form.save(organizer=request.user, commit=True)
            # Привязываем формсет к созданному событию и сохраняем тарифы
            formset.instance = event
            formset.save()

            if "submit_for_moderation" in request.POST:
                # Если нажата кнопка "Отправить на модерацию", проверяем тарифы
                if _event_has_active_tariff(event):
                    event.status = Event.Status.PENDING
                    event.save(update_fields=["status"])
                    messages.success(request, "Событие отправлено на модерацию.")
                else:
                    # Если нет активных тарифов, не разрешаем отправку на модерацию
                    messages.warning(
                        request,
                        "Нельзя отправить на модерацию без активных тарифов с положительным остатком. "
                        "Сохранено как черновик."
                    )
            else:
                messages.success(request, "Черновик события сохранён.")

            return redirect("events:my_events")

        else:
            messages.error(request, "Проверьте форму: есть ошибки в данных или тарифах.")
    else:
        # GET-запрос: отображаем пустые формы
        form = EventForm()
        formset = EventTariffFormSet()

    return render(request, "events/form.html", {
        "form": form,
        "formset": formset,
        "is_edit": False,
    })

@login_required
def my_event_edit(request, pk: int):
    """
    Редактирование мероприятия организатором.
    Логика разделена: полное редактирование (черновик/отклонено) 
    или ограниченное через EventEditRequest (опубликовано).
    """
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    # === Вариант А: событие еще не опубликовано (или отклонено) — разрешаем полное редактирование ===
    if event.status in (Event.Status.DRAFT, Event.Status.PENDING, Event.Status.REJECTED):
        if request.method == "POST":
            form = EventForm(request.POST, request.FILES, instance=event)
            formset = EventTariffFormSet(request.POST, instance=event)
            if form.is_valid() and formset.is_valid():
                # Сохраним событие и тарифы
                form.save(organizer=request.user, commit=True)
                formset.save()

                # Кнопка "Отправить на модерацию"
                if "submit_for_moderation" in request.POST:
                    if _event_has_active_tariff(event):
                        event.status = Event.Status.PENDING
                        event.moderation_comment = ""
                        event.save(update_fields=["status", "moderation_comment"])
                        messages.success(request, "Событие отправлено на модерацию.")
                    else:
                        messages.error(request, "Нужен хотя бы один активный тариф с остатком.")

                # Иначе — остаётся черновиком/ожидающим (в зависимости от текущего статуса)
                else:
                    messages.success(request, "Черновик сохранён.")

                return redirect("events:my_events")
            else:
                messages.error(request, "Проверьте форму: есть ошибки в данных или тарифах.")
        else:
            form = EventForm(instance=event)
            formset = EventTariffFormSet(instance=event)

        return render(request, "events/form.html", {
            "form": form,
            "formset": formset,
            "is_edit": True,
        })

    # === Вариант Б: опубликовано — как было: ограниченные правки через EventEditRequest ===
    pending = event.edit_requests.filter(status=EventEditRequest.Status.PENDING).first()
    if pending:
        messages.info(request, "По этому мероприятию уже есть заявка на модерации. Дождитесь решения.")
        return render(request, "events/edit_pending.html", {"event": event, "pending": pending})

    if request.method == "POST":
        form = EventEditRequestForm(request.POST, request.FILES)
        if form.is_valid():
            req = form.save(commit=False)
            req.event = event
            req.submitted_by = request.user
            req.status = EventEditRequest.Status.PENDING
            req.save()
            messages.success(request, "Изменения отправлены на модерацию. После одобрения они появятся на сайте.")
            return redirect("events:my_events")
    else:
        form = EventEditRequestForm(initial={
            "new_description": event.description,
            "new_category": event.category_id,
        })

    return render(request, "events/edit_limited.html", {"event": event, "form": form})


@login_required
def my_event_tickets(request, pk: int):
    #Просмотр списка проданных билетов для конкретного мероприятия организатора.
    if not _require_organizer(request):
        return redirect("users:profile")
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    tickets = (Ticket.objects
               .select_related('user', 'event_tariff', 'event_tariff__tariff')
               .filter(event=event)
               .order_by('-created_at'))
    return render(request, 'events/my_event_tickets.html', {'event': event, 'tickets': tickets})


@login_required
def my_event_tickets_export(request, pk: int):
    #Экспорт списка проданных билетов в формате CSV
    if not _require_organizer(request):
      return redirect("users:profile")

    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    tickets = (Ticket.objects
               .select_related('user', 'event_tariff', 'event_tariff__tariff')
               .filter(event=event)
               .order_by('id'))

    # CSV с BOM, чтобы Excel на Windows корректно читал кириллицу
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f"tickets-event-{event.id}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')  # BOM

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'ID билета', 'Покупатель', 'Email',
        'Тариф', 'Цена', 'Использован',
        'Дата покупки', 'QR-хэш'
    ])
    for t in tickets:
        buyer = t.user.get_full_name() or t.user.username
        email = t.user.email
        tariff = t.event_tariff.tariff.name
        price = str(t.event_tariff.price)
        used = 'Да' if t.is_used else 'Нет'
        created = timezone.localtime(t.created_at).strftime('%d.%m.%Y %H:%M')
        writer.writerow([t.id, buyer, email, tariff, price, used, created, t.qr_hash])

    return response

@login_required
@require_POST
def generate_description_api(request):
    #API-эндпоинт для генерации описания мероприятия с помощью AI (YandexGPT).
    # Разрешим только организаторам и админам
    user = request.user
    if not (getattr(user, "is_organizer", False) or user.is_staff or user.is_superuser):
        return JsonResponse({"error": "Недостаточно прав"}, status=403)

    # Простая защита от частых запросов (5 сек)
    last_ts = request.session.get("ai_last_call_ts")
    now_ts = timezone.now().timestamp()
    if last_ts and now_ts - last_ts < 5:
        return JsonResponse({"error": "Слишком часто. Попробуйте через пару секунд."}, status=429)
    request.session["ai_last_call_ts"] = now_ts

    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Неверный JSON"}, status=400)

    # Собираем контекст: можно передать title/date/location/category/keywords
    title = (body.get("title") or "").strip()
    date_time = (body.get("starts_at") or "").strip()  # строка (мы не парсим тут)
    location = (body.get("location") or "").strip()
    category = (body.get("category_name") or "").strip()
    keywords = (body.get("keywords") or "").strip()

    if not (title or keywords):
        return JsonResponse({"error": "Укажите как минимум название или ключевые слова"}, status=400)

    # Сформируем user‑промпт из полей формы
    parts = []
    if title: parts.append(f"Название: {title}")
    if category: parts.append(f"Категория: {category}")
    if date_time: parts.append(f"Дата и время: {date_time}")
    if location: parts.append(f"Локация: {location}")
    if keywords: parts.append(f"Ключевые слова: {keywords}")
    prompt = "Создай привлекательное описание мероприятия по данным:\n" + "\n".join(parts)
    # Вызов сервиса AI
    try:
        text = generate_event_description(prompt)
        return JsonResponse({"text": text})
    except YandexGPTError as e:
        return JsonResponse({"error": str(e)}, status=503)