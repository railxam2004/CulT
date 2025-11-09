from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('', views.home, name='home'), #главная страница
    path('about/', views.about, name='about'), #страница о нас
    path('contacts/', views.contacts, name='contacts'), #страница контакты
]
