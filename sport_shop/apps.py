from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig

class NutShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sport_shop'

    def ready(self):
        import sport_shop.templatetags.custom_filters

class NutShopAdminConfig(AdminConfig):
    default_site = 'sport_shop.admin.SportShopAdminSite'
