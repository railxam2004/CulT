from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from .models import Ticket

@login_required
def my_tickets(request):
    tickets = Ticket.objects.select_related('event', 'event_tariff', 'event_tariff__tariff').filter(user=request.user).order_by('-created_at')
    return render(request, 'tickets/my_tickets.html', {'tickets': tickets})

@login_required
def ticket_view(request, pk: int):
    ticket = get_object_or_404(Ticket.objects.select_related('event', 'event_tariff', 'event_tariff__tariff'), pk=pk, user=request.user)
    return render(request, 'tickets/ticket.html', {'ticket': ticket})