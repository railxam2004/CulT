from django.urls import path
from . import views

app_name = 'favorites'

urlpatterns = [
    path('', views.favorites_list, name='list'),
    path('add/<int:event_id>/', views.favorite_add, name='add'),
    path('remove/<int:event_id>/', views.favorite_remove, name='remove'),
]
