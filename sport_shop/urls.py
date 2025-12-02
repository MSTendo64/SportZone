from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart, name='cart'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('profile/', views.profile, name='profile'),
    path('order-history/', views.order_history, name='order_history'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('payment-success/<int:order_id>/', views.payment_success, name='payment_success'),
    path('payment-by-requisites/<int:order_id>/', views.payment_by_requisites, name='payment_by_requisites'),
    path('confirm-payment/<int:order_id>/', views.confirm_payment, name='confirm_payment'),
    path('add-review/<int:product_id>/', views.add_review, name='add_review'),
    path('my-orders/', views.user_orders, name='user_orders'),
    path('change-password/', views.change_password, name='change_password'),
]
