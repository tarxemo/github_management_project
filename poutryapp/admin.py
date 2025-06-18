from django.apps import apps
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

# Loop through all registered apps
for app_config in apps.get_app_configs():
    models = app_config.get_models()

    # Register each model in the app if not already registered
    for model in models:
        if model in admin.site._registry:
            continue  # Skip already registered models

        # Collect field names for list_display and list_filter
        field_names = [field.name for field in model._meta.fields]

        # Collect field names for search_fields, excluding related fields
        search_field_names = [
            field.name for field in model._meta.fields if not field.is_relation
        ]

        # Dynamically create a ModelAdmin class
        class AutoAdmin(admin.ModelAdmin):
            list_display = field_names
            list_filter = field_names
            search_fields = search_field_names

        try:
            admin.site.register(model, AutoAdmin)
        except AlreadyRegistered:
            pass  # Just in case, though we've already checked
