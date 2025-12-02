from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from sport_shop.admin import admin_site
from sport_shop import views

urlpatterns = [
    path('admin/', admin_site.urls),
    path('panel/', views.panel_dashboard, name='panel_dashboard'),
    path('panel/products/', views.panel_products, name='panel_products'),
    path('panel/products/add/', views.panel_product_edit, name='panel_product_add'),
    path('panel/products/<int:product_id>/edit/', views.panel_product_edit, name='panel_product_edit'),
    path('panel/products/<int:product_id>/delete/', views.panel_product_delete, name='panel_product_delete'),
    path('panel/categories/', views.panel_categories, name='panel_categories'),
    path('panel/categories/<int:category_id>/delete/', views.panel_category_delete, name='panel_category_delete'),
    path('panel/discounts/', views.panel_discounts, name='panel_discounts'),
    path('panel/discounts/add/', views.panel_discount_edit, name='panel_discount_add'),
    path('panel/discounts/<int:discount_id>/edit/', views.panel_discount_edit, name='panel_discount_edit'),
    path('panel/discounts/<int:discount_id>/delete/', views.panel_discount_delete, name='panel_discount_delete'),
    path('panel/users/', views.panel_users, name='panel_users'),
    path('panel/users/<int:user_id>/edit/', views.panel_user_edit, name='panel_user_edit'),
    path('panel/orders/', views.panel_orders, name='panel_orders'),
    path('panel/orders/<int:order_id>/', views.panel_order_detail, name='panel_order_detail'),
    path('', include('sport_shop.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
