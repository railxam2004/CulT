# events/urls.py
from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # --- Кабинет организатора (сначала, чтобы не перехватил slug-роут) ---
    path('my-events/', views.my_events, name='my_list'),
    path('my-events/create/', views.my_event_create, name='create'),
    path('my-events/<int:pk>/edit/', views.my_event_edit, name='edit'),

    # --- Публичные ---
    path('', views.event_list, name='list'),
    path('category/<slug:slug>/', views.event_list, name='category'),
    path('<slug:slug>/', views.event_detail, name='detail'),  # теперь по слагу
]
