# urls.py
from django.urls import path

from . import views
from .views import CreateOrderAPIView, OrderDetailView, OrderListView, VnpayReturn

urlpatterns = [
    path('view/', views.view_cart, name='view_cart'),
    path('add/', views.add_product_to_cart, name='add_product_to_cart'),
    path('update/', views.update_product_in_cart, name='update_product_in_cart'),
    path('remove/', views.remove_product_from_cart, name='remove_product_from_cart'),
    path('create_order/', CreateOrderAPIView.as_view(), name='create-order'),
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('detail_orders/', OrderDetailView.as_view(), name='order-detail'),
    path('vnpay/',VnpayReturn.as_view(), name='vnpay-return'),
]
