from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls), #админка

    path('', include('pages.urls')), #статичные страницы(главная, о нас, контакты)
    path('users/', include('users.urls')), #регистрация, авторизация, профиль
    path('events/', include('events.urls')), #мероприятия
    path('tickets/', include('tickets.urls')), #билеты
    path('favorites/', include('favorites.urls')), #избранное
    path('cart/', include('cart.urls')), #корзина
    path('dashboard/', include('dashboard.urls')), #панель организатора
    path('payments/', include('payments.urls', namespace='payments')), #платежи
]

# Обслуживание медиа-файлов в режиме отладки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
