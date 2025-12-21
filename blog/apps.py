from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog'
    verbose_name = "5. 📝 وبلاگ"

    def ready(self):
        """Override taggit admin after everything is loaded"""
        from django.contrib import admin
        from taggit.models import Tag
        from django.utils.html import format_html

        # Unregister taggit's default admin
        admin.site.unregister(Tag)

        # Register our custom admin
        @admin.register(Tag)
        class TagAdmin(admin.ModelAdmin):
            list_display = ['name', 'slug', 'posts_count']
            search_fields = ['name', 'slug']
            readonly_fields = ['slug']

            def posts_count(self, obj):
                count = obj.taggit_taggeditem_items.filter(
                    content_type__model='post'
                ).count()

                if count > 0:
                    return format_html(
                        '<span style="background: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
                        count
                    )
                return format_html('<span style="color: #999;">0</span>')

            posts_count.short_description = 'تعداد پست‌ها'

