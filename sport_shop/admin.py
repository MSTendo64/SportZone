from django.contrib import admin
from django.db import models
from django.forms import Textarea, TextInput
from django.utils.html import format_html
from django.shortcuts import get_object_or_404
from .models import Category, Product, ProductVariant, Order, OrderItem, PaymentMethod, UserProfile, ProductImage, Review, SiteSettings
from .templatetags.custom_filters import custom_format
from django.urls import path, reverse
from django.template.response import TemplateResponse

class SportShopAdminSite(admin.AdminSite):
    site_header = 'SportZone Администрирование'
    site_title = 'SportZone'
    index_title = 'Панель управления'

admin_site = SportShopAdminSite(name='sport_shop_admin')

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ('user', 'rating', 'text', 'created_at')

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'average_rating', 'preview_button')
    list_filter = ('category',)
    inlines = [ProductImageInline, ProductVariantInline, ReviewInline]
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 10, 'cols': 80})},
        models.CharField: {'widget': TextInput(attrs={'size': '80'})},
    }

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:product_id>/preview/', self.admin_site.admin_view(self.product_preview), name='product_preview'),
        ]
        return custom_urls + urls

    def product_preview(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        formatted_description = custom_format(product.formatted_description())
        context = {
            'product': product,
            'formatted_description': formatted_description,
        }
        return TemplateResponse(request, 'admin/product_preview.html', context)

    def preview_button(self, obj):
        return format_html(
            '<a class="button" href="{}">Предпросмотр</a>',
            reverse('admin:product_preview', args=[obj.pk])
        )
    preview_button.short_description = 'Предпросмотр'

    def average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews:
            return sum(review.rating for review in reviews) / len(reviews)
        return 0
    average_rating.short_description = 'Средний рейтинг'

# Регистрация моделей
admin_site.register(Category)
admin_site.register(Product, ProductAdmin)
admin_site.register(ProductVariant)
admin_site.register(Order)
admin_site.register(OrderItem)
admin_site.register(PaymentMethod)
admin_site.register(UserProfile)
admin_site.register(ProductImage)
admin_site.register(Review)
admin_site.register(SiteSettings)

from .models import Discount
admin_site.register(Discount)

# Здесь вы можете добавить кастомные классы админки для каждой модели, если это необходимо
