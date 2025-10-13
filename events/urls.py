from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # кабинет организатора
    path('my-events/', views.my_events, name='my_events'),
    path('my-events/create/', views.my_event_create, name='create'),
    path('my-events/<int:pk>/edit/', views.my_event_edit, name='edit'),
    path('my-events/<int:pk>/tickets/', views.my_event_tickets, name='my_event_tickets'),
    path('my-events/<int:pk>/tickets/export/', views.my_event_tickets_export, name='my_event_tickets_export'),  # <-- NEW
    path('my-events/<int:id>/edit/', views.my_event_edit, name='my_event_edit'),
    path('ai/generate-description/', views.generate_description_api, name='generate_description_api'),
    
    # публичные
    path('', views.event_list, name='list'),
    path('category/<slug:slug>/', views.event_list, name='category'),
    path('<slug:slug>/', views.event_detail, name='detail'),
]