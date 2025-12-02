from .models import Category, SiteSettings
from django.core.cache import cache


def categories_and_settings(request):
    """
    Контекстный процессор для категорий и настроек сайта.
    
    Примечание: Для улучшения производительности можно использовать кэширование:
    - Категории кэшируются на 1 час (они редко меняются)
    - Логотип кэшируется на 1 час
    """
    # Кэшируем категории на 1 час (3600 секунд)
    categories = cache.get('all_categories')
    if categories is None:
        categories = list(Category.objects.all())
        cache.set('all_categories', categories, 3600)
    
    # Кэшируем логотип на 1 час
    logo_url = cache.get('site_logo_url')
    if logo_url is None:
        logo_url = SiteSettings.get_logo()
        cache.set('site_logo_url', logo_url, 3600)
    
    return {
        'categories': categories,
        'logo_url': logo_url
    }
