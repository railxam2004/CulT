from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # кабинет организатора
    path('my-events/', views.my_events, name='my_events'), # список моих мероприятий
    path('my-events/create/', views.my_event_create, name='create'), # создание мероприятия
    path('my-events/<int:pk>/edit/', views.my_event_edit, name='edit'), # редактирование мероприятия
    path('my-events/<int:pk>/tickets/', views.my_event_tickets, name='my_event_tickets'), # управление билетами мероприятия
    path('my-events/<int:pk>/tickets/export/', views.my_event_tickets_export, name='my_event_tickets_export'), # экспорт билетов
    path('ai/generate-description/', views.generate_description_api, name='generate_description_api'), # генерация описания через YandexGPT

    # публичные
    path('', views.event_list, name='list'), # список мероприятий
    path('category/<slug:slug>/', views.event_list, name='category'), # список мероприятий по категории
    path('<slug:slug>/', views.event_detail, name='detail'), # детальная страница мероприятия
]