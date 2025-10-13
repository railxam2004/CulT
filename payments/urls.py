from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # старт оплаты ЮKassa: создаёт Order из корзины и редиректит на confirmation_url
    path('yookassa/start/', views.yk_start, name='yookassa_start'),

    # вебхук от ЮKassa (для прод/туннеля). Сейчас опционально.
    path('yookassa/webhook/', views.yk_webhook, name='yookassa_webhook'),
]