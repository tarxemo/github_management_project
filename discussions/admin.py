from django.contrib import admin
from .models import Topic, Thread, Post

# @admin.register(Topic)
# class TopicAdmin(admin.ModelAdmin):
#     list_display = ("name", "is_archived", "created_at")
#     prepopulated_fields = {"slug": ("name",)}

# @admin.register(Thread)
# class ThreadAdmin(admin.ModelAdmin):
#     list_display = ("title", "topic", "author", "is_locked", "is_pinned", "created_at")
#     list_filter = ("topic", "is_locked", "is_pinned")
#     search_fields = ("title", "body_md")
#     prepopulated_fields = {"slug": ("title",)}

# @admin.register(Post)
# class PostAdmin(admin.ModelAdmin):
#     list_display = ("thread", "author", "is_deleted", "created_at")
#     search_fields = ("body_md",)
#     list_filter = ("is_deleted",)
