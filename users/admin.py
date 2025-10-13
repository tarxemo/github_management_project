from django.apps import apps
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered


def auto_register_all_models():
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            if model in admin.site._registry:
                continue  # Skip already registered models

            field_names = [field.name for field in model._meta.fields]
            search_field_names = [field.name for field in model._meta.fields if not field.is_relation]

            try:
                class AutoAdmin(admin.ModelAdmin):
                    list_display = field_names
                    list_filter = field_names
                    search_fields = search_field_names

                admin.site.register(model, AutoAdmin)

            except AlreadyRegistered:
                continue
auto_register_all_models()