import jdatetime
from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Post, PostSection, Media, Layout, Author


def datetime2jalali(date_time):
    if not date_time:
        return '-'
    if isinstance(date_time, type(jdatetime.date.today())):
        jdate = jdatetime.date.fromgregorian(date=date_time)
        return jdate.strftime('%Y/%m/%d')

    jdate = jdatetime.datetime.fromgregorian(datetime=date_time)
    return jdate.strftime('%Y/%m/%d - %H:%M')


def date2jalali(date_obj):
    if not date_obj:
        return '-'
    jdate = jdatetime.date.fromgregorian(date=date_obj)
    return jdate.strftime('%Y/%m/%d')


class PostSectionInline(admin.TabularInline):
    model = PostSection
    extra = 1
    fields = ['section_type', 'order', 'position_choice', 'position_x', 'position_y', 'width', 'height']
    ordering = ['order']


class MediaInline(admin.TabularInline):
    model = Media
    extra = 0
    fields = ['file', 'file_type', 'alt_text', 'caption', 'get_file_size_display']
    readonly_fields = ['get_file_size_display']

    def get_file_size_display(self, obj):
        return obj.get_file_size_display() if obj.id else '-'

    get_file_size_display.short_description = 'حجم فایل'


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    """ادمین پنل نویسندگان"""

    list_display = [
        'name',
        'avatar_preview',
        'has_social_links',
        'posts_count',
        'created_at',
    ]

    search_fields = ['name', 'bio']

    list_filter = ['created_at']

    readonly_fields = ['avatar_preview', 'created_at']

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'avatar', 'avatar_preview', 'bio')
        }),
        ('شبکه‌های اجتماعی', {
            'fields': ('twitter', 'instagram', 'linkedin', 'website'),
            'classes': ('collapse',),
        }),
        ('زمان', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover;"/>',
                obj.avatar.url
            )
        return '—'

    avatar_preview.short_description = 'پیش‌نمایش آواتار'

    def has_social_links(self, obj):
        count = sum([
            bool(obj.twitter),
            bool(obj.instagram),
            bool(obj.linkedin),
            bool(obj.website),
        ])
        if count > 0:
            return format_html(
                '<span style="color: #28a745;">✓ {} لینک</span>',
                count
            )
        return format_html('<span style="color: #999;">—</span>')

    has_social_links.short_description = 'شبکه‌های اجتماعی'

    def posts_count(self, obj):
        return obj.posts.count()

    posts_count.short_description = 'تعداد پست‌ها'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'editor',
        'authors_list',
        'status_badge',
        'get_sections_count',
        'jalali_published_at',
        'jalali_created_at',
        'featured_image_preview'
    ]

    list_filter = [
        'status',
        'created_at',
        'published_at',
        'editor',
    ]

    search_fields = [
        'title',
        'slug',
        'meta_description',
        'editor__username',
        'editor__email',
        'authors__name',
    ]

    readonly_fields = [
        'editor',
        'created_at',
        'updated_at',
        'get_sections_count',
        'featured_image_preview',
    ]

    prepopulated_fields = {'slug': ('title',)}

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('title', 'slug', 'authors', 'status')
        }),
        ('محتوا', {
            'fields': ('featured_image', 'featured_image_preview', 'meta_description'),
            'description': 'تصویر شاخص و توضیحات SEO'
        }),
        ('زمان‌بندی', {
            'fields': ('published_at', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
        ('آمار', {
            'fields': ('get_sections_count',),
            'classes': ('collapse',),
        }),
    )
    filter_horizontal = ['authors']
    inlines = [PostSectionInline, MediaInline]

    date_hierarchy = 'created_at'

    actions = ['publish_posts', 'draft_posts', 'archive_posts']

    def save_model(self, request, obj, form, change):
        """Automatically get the author from the current user"""
        if not obj.pk:
            obj.editor = request.user  #
        super().save_model(request, obj, form, change)

    def authors_list(self, obj):
        authors = obj.authors.all()
        if authors:
            names = ', '.join([author.name for author in authors])
            return format_html(
                '<span style="color: #666;">{}</span>',
                names
            )
        return '—'

    authors_list.short_description = 'نویسندگان'

    def jalali_published_at(self, obj):
        if not obj.published_at:
            if obj.status == 'draft':
                return format_html('<span style="color: #6c757d;">پیش‌نویس</span>')
            elif obj.status == 'archived':
                return format_html('<span style="color: #dc3545;">بایگانی شده</span>')
            return '-'

        jalali_date = datetime2jalali(obj.published_at)
        return format_html(
            '<span style="color: #28a745;">{}</span>',
            jalali_date
        )

    jalali_published_at.short_description = 'تاریخ انتشار'
    jalali_published_at.admin_order_field = 'published_at'

    def jalali_created_at(self, obj):
        return datetime2jalali(obj.created_at)

    jalali_created_at.short_description = 'تاریخ ایجاد'
    jalali_created_at.admin_order_field = 'created_at'

    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'published': '#28a745',
            'archived': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#000'),
            obj.get_status_display()
        )

    status_badge.short_description = 'وضعیت'
    status_badge.admin_order_field = 'status'

    def get_sections_count(self, obj):
        return obj.sections.count()

    get_sections_count.short_description = 'تعداد بخش‌ها'

    def featured_image_preview(self, obj):
        """Featured Image Preview"""
        if obj.featured_image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 5px;"/>',
                obj.featured_image.url
            )
        return '-'

    featured_image_preview.short_description = 'پیش‌نمایش تصویر'

    def publish_posts(self, request, queryset):
        """Action: Publish selected posts"""
        from django.utils import timezone
        updated = 0
        for post in queryset:
            if post.status != 'published':
                post.status = 'published'
                if not post.published_at:
                    post.published_at = timezone.now()
                post.save()
                updated += 1
        self.message_user(request, f'{updated} پست منتشر شد.')

    publish_posts.short_description = 'انتشار پست‌های انتخابی'

    def draft_posts(self, request, queryset):
        """Action: Draft selected posts"""
        updated = queryset.update(status='draft')
        self.message_user(request, f'{updated} پست به پیش‌نویس تبدیل شد.')

    draft_posts.short_description = 'پیش‌نویس کردن پست‌های انتخابی'

    def archive_posts(self, request, queryset):
        """Action: Archive selected posts"""
        updated = queryset.update(status='archived')
        self.message_user(request, f'{updated} پست بایگانی شد.')

    archive_posts.short_description = 'بایگانی پست‌های انتخابی'

    def get_queryset(self, request):
        """
        Retrieve the queryset for this admin view with query optimizations.

        - Uses `select_related('author')` to perform a SQL join and fetch related
          author objects in the same query, reducing database hits.
        - Annotates each Post instance with `sections_count`, representing the
          number of related PostSection objects, using `Count('sections')`.

        Avoiding additional queries for author and section count.
        """
        qs = super().get_queryset(request)
        return qs.select_related('editor').prefetch_related('authors').annotate(
            sections_count=Count('sections')
        )


@admin.register(PostSection)
class PostSectionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'post',
        'section_type_badge',
        'order',
        'position_choice',
        'content_preview',
    ]

    list_filter = [
        'section_type',
        'position_choice',
        'post__status',
    ]

    search_fields = [
        'post__title',
        'content',
    ]

    list_editable = ['order']

    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('post', 'section_type', 'content', 'order')
        }),
        ('موقعیت و اندازه', {
            'fields': (
                'position_choice',
                ('position_x', 'position_y'),
                ('width', 'height')
            ),
            'description': 'برای استفاده از موقعیت دلخواه، گزینه "سفارشی" را انتخاب کنید'
        }),
    )

    raw_id_fields = ['post']

    def section_type_badge(self, obj):
        icons = {
            'text': '📝',
            'image': '🖼️',
            'gallery': '🎨',
            'quote': '💬',
            'code': '💻',
            'video': '🎬',
        }
        return format_html(
            '{} {}',
            icons.get(obj.section_type, ''),
            obj.get_section_type_display()
        )

    section_type_badge.short_description = 'نوع'
    section_type_badge.admin_order_field = 'section_type'

    def content_preview(self, obj):
        if obj.content:
            preview = obj.content[:50]
            if len(obj.content) > 50:
                preview += '...'
            return preview
        return '-'

    content_preview.short_description = 'پیش‌نمایش محتوا'

    def get_queryset(self, request):
        """query optimizations"""
        qs = super().get_queryset(request)
        return qs.select_related('post')


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'post',
        'file_type_badge',
        'file_preview',
        'get_file_size_display',
        'alt_text',
        'jalali_created_at',
    ]

    list_filter = [
        'file_type',
        'created_at',
        'post__status',
    ]

    search_fields = [
        'post__title',
        'alt_text',
        'caption',
    ]

    readonly_fields = [
        'file_size',
        'get_file_size_display',
        'width',
        'height',
        'created_at',
        'file_preview',
    ]

    fieldsets = (
        ('اطلاعات فایل', {
            'fields': ('post', 'section', 'file', 'file_type', 'file_preview')
        }),
        ('توضیحات', {
            'fields': ('alt_text', 'caption')
        }),
        ('مشخصات فنی', {
            'fields': ('width', 'height', 'file_size', 'get_file_size_display', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    raw_id_fields = ['post', 'section']

    date_hierarchy = 'created_at'

    def file_type_badge(self, obj):
        icons = {
            'image': '🖼️',
            'video': '🎬',
            'audio': '🎵',
        }
        colors = {
            'image': '#17a2b8',  # آبی
            'video': '#dc3545',  # قرمز
            'audio': '#28a745',  # سبز
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{} {}</span>',
            colors.get(obj.file_type, '#000'),
            icons.get(obj.file_type, ''),
            obj.get_file_type_display()
        )

    file_type_badge.short_description = 'نوع فایل'
    file_type_badge.admin_order_field = 'file_type'

    def file_preview(self, obj):
        if obj.is_image and obj.file:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px; border-radius: 5px;"/>',
                obj.file.url
            )
        elif obj.is_video and obj.file:
            return format_html(
                '<video width="200" controls><source src="{}"></video>',
                obj.file.url
            )
        elif obj.is_audio and obj.file:
            return format_html(
                '<audio controls><source src="{}"></audio>',
                obj.file.url
            )
        return '-'

    file_preview.short_description = 'پیش‌نمایش'

    def jalali_created_at(self, obj):
        return datetime2jalali(obj.created_at)

    jalali_created_at.short_description = 'تاریخ ایجاد'
    jalali_created_at.admin_order_field = 'created_at'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('post', 'section')


@admin.register(Layout)
class LayoutAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'is_active',
        'thumbnail_preview',
        'jalali_created_at',
    ]

    list_filter = [
        'is_active',
        'created_at',
    ]

    search_fields = [
        'name',
        'description',
    ]

    list_editable = ['is_active']

    readonly_fields = ['thumbnail_preview', 'created_at']

    fieldsets = (
        ('اطلاعات قالب', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('تنظیمات', {
            'fields': ('template_json',),
            'description': 'تنظیمات JSON این قالب'
        }),
        ('نمایش', {
            'fields': ('thumbnail', 'thumbnail_preview'),
        }),
        ('زمان', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 200px; border-radius: 5px;"/>',
                obj.thumbnail.url
            )
        return '-'

    thumbnail_preview.short_description = 'پیش‌نمایش'

    def jalali_created_at(self, obj):
        return datetime2jalali(obj.created_at)

    jalali_created_at.short_description = 'تاریخ ایجاد'
    jalali_created_at.admin_order_field = 'created_at'
# Admin panel appearance settings
# admin.site.site_header = 'پنل مدیریت بلاگ'
# admin.site.site_title = 'ادمین بلاگ'
# admin.site.index_title = 'مدیریت محتوا'
