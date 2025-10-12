from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from .models import Ticket
from .utils import build_ticket_pdf

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