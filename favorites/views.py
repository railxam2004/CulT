from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from events.models import Event
from .models import Favorite

@login_required
#    Просмотр списка избранных мероприятий пользователя.
def favorites_list(request):
    qs = (Favorite.objects
          .filter(user=request.user)
          .select_related('event', 'event__category', 'event__organizer')
          .order_by('-created_at'))
    paginator = Paginator(qs, 12)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    return render(request, 'favorites/list.html', {'favorites': page_obj})

@login_required
#    Добавление мероприятия в избранное.
def favorite_add(request, event_id: int):
    if request.method != 'POST':
        event = get_object_or_404(Event, pk=event_id)
        return redirect('events:detail', slug=event.slug)
    event = get_object_or_404(Event, pk=event_id, status=Event.Status.PUBLISHED, is_active=True)
    Favorite.objects.get_or_create(user=request.user, event=event)
    messages.success(request, 'Добавлено в избранное.')
    nxt = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('favorites:list')
    return redirect(nxt)

@login_required
#    Удаление мероприятия из избранного.
def favorite_remove(request, event_id: int):
    if request.method != 'POST':
        event = get_object_or_404(Event, pk=event_id)
        return redirect('events:detail', slug=event.slug)
    Favorite.objects.filter(user=request.user, event_id=event_id).delete()
    messages.info(request, 'Убрано из избранного.')
    nxt = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('favorites:list')
    return redirect(nxt)
