# users/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    # аутентификация
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # регистрация
    path('register/', views.register, name='register'),

    # профиль
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),

    # смена пароля
    path('profile/password/', views.MyPasswordChangeView.as_view(), name='password_change'),
    path('profile/password/done/', views.MyPasswordChangeDoneView.as_view(), name='password_change_done'),

    # заявка на статус организатора
    path('profile/organizer-request/', views.organizer_request, name='organizer_request'),
]
