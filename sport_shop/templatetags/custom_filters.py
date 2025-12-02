from django import template
from django.utils.safestring import mark_safe
from sport_shop.models import ProductVariant
import re

register = template.Library()

@register.filter(name='custom_format')
def custom_format(value):
    if not isinstance(value, str):
        return value

    # Обработка тега <b> и <strong>
    value = re.sub(r'<b>(.*?)</b>', r'<strong>\1</strong>', value, flags=re.DOTALL)
    
    # Обработка тегов <i>, <u>
    value = re.sub(r'<i>(.*?)</i>', r'<em>\1</em>', value, flags=re.DOTALL)
    value = re.sub(r'<u>(.*?)</u>', r'<u>\1</u>', value, flags=re.DOTALL)
    
    # Обработка тега <link> - создаем ссылку с визуальным выделением
    def link_replace(match):
        url = match.group(1).strip()
        text = match.group(2).strip()
        # Добавляем иконку и стили для визуального выделения
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="formatted-link"><i class="fas fa-external-link-alt" style="font-size: 0.85em; margin-right: 3px;"></i>{text}</a>'
    
    # Обработка тега link - более гибкое регулярное выражение
    value = re.sub(r'<link\s*=\s*["\']([^"\']+)["\']\s*>(.*?)</link>', link_replace, value, flags=re.DOTALL | re.IGNORECASE)
    
    # Обработка тега <color> - применяем цвет с повышенной важностью
    def color_replace(match):
        color = match.group(1).strip()
        text = match.group(2)
        # Убеждаемся, что цвет в правильном формате
        if not color.startswith('#'):
            color = '#' + color
        # Проверяем формат цвета (должен быть #RRGGBB)
        if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
            # Если формат неправильный, используем стандартный цвет
            return f'<span class="formatted-color" style="color: {color} !important; font-weight: 500;">{text}</span>'
        return f'<span class="formatted-color" style="color: {color} !important; font-weight: 500;">{text}</span>'
    
    # Обработка тега color - более гибкое регулярное выражение
    value = re.sub(r'<color\s*=\s*["\']([^"\']+)["\']\s*>(.*?)</color>', color_replace, value, flags=re.DOTALL | re.IGNORECASE)
    
    # Обработка тега <p>
    value = re.sub(r'<p>(.*?)</p>', r'<p class="formatted-paragraph">\1</p>', value, flags=re.DOTALL)
    
    # Обработка тега <image>
    def image_replace(match):
        url = match.group(1)
        return f'<div class="formatted-image-wrapper"><img src="{url}" alt="Изображение" class="formatted-image" loading="lazy"></div>'
    
    value = re.sub(r'<image>(.*?)</image>', image_replace, value, flags=re.DOTALL)
    
    # Обработка переносов строк
    value = value.replace('\n', '<br>')
    
    return mark_safe(value)

@register.filter(name='plain_text')
def plain_text(value):
    if not isinstance(value, str):
        return value
    
    # Удаляем все кастомные теги
    value = re.sub(r'<i>(.*?)</i>', r'\1', value)
    value = re.sub(r'<u>(.*?)</u>', r'\1', value)
    value = re.sub(r'<link="(.*?)">(.*?)</link>', r'\2', value)
    value = re.sub(r'<color="(#[0-9A-Fa-f]{6})">(.*?)</color>', r'\2', value)
    value = re.sub(r'<p>(.*?)</p>', r'\1', value)
    value = re.sub(r'<image>.*?</image>', '', value)
    
    return value

@register.filter(name='get_variant')
def get_variant(variant_id):
    """Получить вариант продукта по ID. Возвращает None, если не найден."""
    try:
        return ProductVariant.objects.get(id=variant_id)
    except ProductVariant.DoesNotExist:
        return None
