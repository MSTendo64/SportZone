from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg, Min
from math import ceil
from django.utils.safestring import mark_safe
import re

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
    
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='Категория')
    formatted_description_text = models.TextField(
        blank=True,
        verbose_name='Форматированное описание',
        help_text="Используйте теги <i>, <u>, <link>, <color>, <p>, <image> для форматирования"
    )
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'

    def __str__(self):
        return self.name

    @property
    def main_image(self):
        return self.images.first()

    @property
    def average_rating(self):
        avg = self.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        return ceil(avg)

    def get_cheapest_variant(self):
        return self.variants.order_by('price').first()

    @staticmethod
    def _video_preview(match):
        """Обработка тега <vid> для вставки видео."""
        video_url = match.group(1)
        
        # YouTube
        youtube_match = re.search(r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]+)', video_url)
        if youtube_match:
            video_id = youtube_match.group(1)
            return f'''
            <div class="video-container">
                <iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" 
                        frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; 
                        gyroscope; picture-in-picture" allowfullscreen></iframe>
            </div>
            '''
        
        # Vimeo
        vimeo_match = re.search(r'vimeo\.com\/(\d+)', video_url)
        if vimeo_match:
            video_id = vimeo_match.group(1)
            return f'''
            <div class="video-container">
                <iframe src="https://player.vimeo.com/video/{video_id}" width="560" height="315" 
                        frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>
            </div>
            '''
        
        # Другие видео (используем HTML5 video player)
        return f'''
        <div class="video-container">
            <video width="560" height="315" controls>
                <source src="{video_url}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
        '''

    def formatted_description(self):
        """Возвращает отформатированное описание продукта."""
        desc = self.formatted_description_text or self.description
        # Обработка тега <b>
        desc = re.sub(r'<b>(.*?)</b>', r'<strong>\1</strong>', desc)
        # Обработка тега <vid>
        desc = re.sub(r'<vid>(.*?)</vid>', self._video_preview, desc)
        return mark_safe(desc)

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name='Товар')
    image = models.ImageField(upload_to='products/', verbose_name='Изображение')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        ordering = ['order']
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'

    def __str__(self):
        return f"Изображение {self.order} для {self.product.name}"

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants', verbose_name='Товар')
    weight = models.IntegerField(help_text="Вес в граммах", verbose_name='Вес (г)')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')

    class Meta:
        verbose_name = 'Вариант товара'
        verbose_name_plural = 'Варианты товаров'

    def __str__(self):
        return f"{self.product.name} - {self.weight}г"

    @property
    def price_per_kg(self):
        return self.price / self.weight if self.weight else 0

class PaymentMethod(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    shop_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='Shop ID')
    secret_key = models.CharField(max_length=100, blank=True, null=True, verbose_name='Секретный ключ')
    bank_account = models.CharField(max_length=200, blank=True, null=True, verbose_name='Банковский счет')

    class Meta:
        verbose_name = 'Способ оплаты'
        verbose_name_plural = 'Способы оплаты'

    def __str__(self):
        return self.name
    
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending_payment', 'Ожидает оплаты'),
        ('processing', 'Подготовка'),
        ('shipped', 'Отправлено'),
        ('delivered', 'Доставлено'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Общая сумма')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment', verbose_name='Статус')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True, verbose_name='Способ оплаты')
    full_name = models.CharField(max_length=200, verbose_name='Полное имя')
    address = models.TextField(verbose_name='Адрес')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    is_completed = models.BooleanField(default=False, verbose_name='Завершен')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ {self.id} - {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name='Заказ')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='orderitems', verbose_name='Вариант товара')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')

    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'

    def __str__(self):
        return f"{self.product_variant.product.name} - {self.quantity} шт."

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return self.user.username

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='Товар')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], verbose_name='Рейтинг')
    text = models.TextField(verbose_name='Текст отзыва')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']

    def __str__(self):
        return f"Отзыв на {self.product.name} от {self.user.username}"

class SiteSettings(models.Model):
    logo = models.ImageField(upload_to='logo/', null=True, blank=True)

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def __str__(self):
        return 'Настройки сайта'

    @classmethod
    def get_logo(cls):
        settings = cls.objects.first()
        if settings and settings.logo:
            return settings.logo.url
        return None


class Discount(models.Model):
    """Модель для скидок на товары, категории или общих скидок."""
    DISCOUNT_TYPE_CHOICES = [
        ('product', 'На товар'),
        ('category', 'На категорию'),
        ('all', 'На все товары'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Название скидки')
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, verbose_name='Тип скидки')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Товар')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Категория')
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Процент скидки')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Фиксированная сумма скидки')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    start_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата начала')
    end_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата окончания')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Скидка'
        verbose_name_plural = 'Скидки'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.discount_percent}%"
    
    def calculate_discount(self, price):
        """Рассчитать цену со скидкой."""
        if self.discount_amount:
            return max(0, price - self.discount_amount)
        return price * (1 - self.discount_percent / 100)
