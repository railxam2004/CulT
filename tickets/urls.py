from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('my-tickets/', views.my_tickets, name='my_tickets'),
    path('ticket/<int:pk>/', views.ticket_view, name='ticket_view'),
    path('ticket/<int:pk>/pdf/', views.ticket_pdf, name='ticket_pdf'),

    # сканер и переключение статуса
    path('scan/', views.scan_ticket, name='scan'),
    path('scan/event/<int:event_id>/', views.scan_ticket, name='scan_event'),
    path('toggle-used/<int:pk>/', views.toggle_ticket_used, name='toggle_used'),
]
