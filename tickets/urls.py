from django.urls import path
from . import views

app_name = 'tickets'
urlpatterns = [
    path('my-tickets/', views.my_tickets, name='my_tickets'),
    path('ticket/<int:pk>/', views.ticket_view, name='ticket_view'),
]