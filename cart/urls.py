# cart/urls.py
from django.urls import path
from . import views

app_name = 'cart'
urlpatterns = [
    path('', views.cart_view, name='view'),
    path('add/<int:event_tariff_id>/', views.add_to_cart, name='add'),
    path('update/<int:item_id>/', views.cart_update, name='update'),
    path('remove/<int:item_id>/', views.cart_remove, name='remove'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/success/<int:order_id>/', views.checkout_success, name='checkout_success'),
    path('checkout/cancel/<int:order_id>/', views.checkout_cancel, name='checkout_cancel'),
]
