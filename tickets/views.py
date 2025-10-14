from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from .models import Ticket
from .utils import build_ticket_pdf
import re
from django.contrib import messages
from events.models import Event

@login_required
def my_tickets(request):
    tickets = Ticket.objects.select_related('event', 'event_tariff', 'event_tariff__tariff').filter(user=request.user).order_by('-created_at')
    return render(request, 'tickets/my_tickets.html', {'tickets': tickets})

@login_required
def ticket_view(request, pk: int):
    ticket = get_object_or_404(Ticket.objects.select_related('event', 'event_tariff', 'event_tariff__tariff'), pk=pk, user=request.user)
    return render(request, 'tickets/ticket.html', {'ticket': ticket})

@login_required
def ticket_pdf(request, pk: int):
    ticket = get_object_or_404(
        Ticket.objects.select_related('user', 'event', 'event_tariff', 'event__organizer'),
        pk=pk
    )

    is_owner = (ticket.user_id == request.user.id)
    is_event_organizer = (request.user.is_authenticated and request.user.is_organizer and ticket.event.organizer_id == request.user.id)
    is_admin = (request.user.is_staff or request.user.is_superuser)

    if not (is_owner or is_event_organizer or is_admin):
        return HttpResponseForbidden("У вас нет прав для скачивания этого билета.")

    pdf_bytes = build_ticket_pdf(ticket)
    filename = f"ticket-{ticket.pk}-{ticket.event.slug}.pdf"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

# --- helper: проверка прав ---
def _is_admin(user):
    return user.is_staff or user.is_superuser

def _can_manage_ticket(user, ticket: Ticket):
    return _is_admin(user) or (getattr(user, "is_organizer", False) and ticket.event.organizer_id == user.id)

def _require_organizer_or_admin(request):
    if not request.user.is_authenticated or not (_is_admin(request.user) or getattr(request.user, "is_organizer", False)):
        messages.info(request, "Доступно только организаторам и администраторам.")
        return False
    return True

# --- парсинг введённого кода из инпута ---
PAYLOAD_RE = re.compile(r'^TICKET:(?P<ticket>\d+)\|HASH:(?P<hash>[a-fA-F0-9]{8,64})\|EVENT:(?P<event>\d+)$')

def _parse_code(code: str):
    """
    Поддерживаем 3 формата:
      1) Полный payload: TICKET:123|HASH:...|EVENT:5
      2) Только qr_hash: 32..64 hex
      3) Только id билета: число
    Возвращает dict с возможными ключами: ticket_id, qr_hash, event_id.
    """
    data = {}
    if not code:
        return data
    code = code.strip()

    m = PAYLOAD_RE.match(code)
    if m:
        data["ticket_id"] = int(m.group("ticket"))
        data["qr_hash"] = m.group("hash").lower()
        data["event_id"] = int(m.group("event"))
        return data

    if re.fullmatch(r'[a-fA-F0-9]{16,64}', code):
        data["qr_hash"] = code.lower()
        return data

    if code.isdigit():
        data["ticket_id"] = int(code)
        return data

    return data

def _locate_ticket(data: dict):
    qs = Ticket.objects.select_related('event', 'event_tariff', 'event_tariff__tariff', 'user')
    # если есть все три — фильтруем строго
    if {'ticket_id','qr_hash','event_id'} <= data.keys():
        t = qs.filter(pk=data['ticket_id'], qr_hash=data['qr_hash'], event_id=data['event_id']).first()
        if t:
            return t
    # далее пробуем по хэшу, иначе по id
    if 'qr_hash' in data:
        t = qs.filter(qr_hash=data['qr_hash']).first()
        if t:
            return t
    if 'ticket_id' in data:
        t = qs.filter(pk=data['ticket_id']).first()
        if t:
            return t
    return None


@login_required
def scan_ticket(request, event_id=None):
    # доступ только организатору/админу
    if not _require_organizer_or_admin(request):
        return redirect("users:profile")

    event = None
    if event_id is not None:
        # органайзер может сканировать только свои события
        event = get_object_or_404(Event, pk=event_id)
        if not (_is_admin(request.user) or event.organizer_id == request.user.id):
            return HttpResponseForbidden("Нет прав для этого события.")

    # --- ДОБАВЛЕННЫЙ БЛОК ---
    if event and event.is_past:
        messages.info(request, "Сканирование закрыто: событие уже прошло.")
        return render(request, "tickets/scan.html", {"event": event, "result": None})
    # -------------------------

    ctx = {"event": event, "result": None}

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        action = request.POST.get("action", "check")  # check | use | unuse
        parsed = _parse_code(code)
        ticket = _locate_ticket(parsed)

        if not ticket:
            messages.error(request, "Билет не найден. Проверьте код.")
            return render(request, "tickets/scan.html", ctx)

        # доп. проверка: если сканируем для конкретного события
        if event and ticket.event_id != event.id:
            messages.error(request, "Этот билет относится к другому событию.")
            return render(request, "tickets/scan.html", ctx)

        if not _can_manage_ticket(request.user, ticket):
            return HttpResponseForbidden("Нет прав на работу с этим билетом.")

        # действие
        if action == "use":
            if ticket.is_used:
                messages.warning(request, "Билет уже был отмечен как использованный.")
            else:
                ticket.is_used = True
                ticket.save(update_fields=["is_used"])
                messages.success(request, "Проход разрешён. Билет отмечен как использованный.")
        elif action == "unuse":
            if not ticket.is_used:
                messages.info(request, "Билет уже отмечен как НЕ использованный.")
            else:
                ticket.is_used = False
                ticket.save(update_fields=["is_used"])
                messages.success(request, "Отметка снята. Билет снова действителен.")
        else:
            # просто проверка без изменения
            messages.info(request, "Билет найден. Можно отметить как использованный.")

        ctx["result"] = ticket

    return render(request, "tickets/scan.html", ctx)
    return render(request, "tickets/scan.html", ctx)


@login_required
def toggle_ticket_used(request, pk: int):
    ticket = get_object_or_404(Ticket.objects.select_related('event'), pk=pk)
    if not _can_manage_ticket(request.user, ticket):
        return HttpResponseForbidden("Нет прав.")
    ticket.is_used = not ticket.is_used
    ticket.save(update_fields=["is_used"])
    messages.success(request, "Статус билета изменён.")
    # вернёмся туда, откуда пришли (список билетов события / сканер)
    return redirect(request.META.get("HTTP_REFERER") or "tickets:scan")