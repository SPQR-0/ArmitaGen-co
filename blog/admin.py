import jdatetime
from django import forms
from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import Post, Author, PostSection, Media, Layout, Comment, CommenterIP


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
        'featured_image_preview',
        'tag_list'
    ]

    list_filter = [
        'status',
        'created_at',
        'published_at',
        'editor',
        'tags',
    ]

    search_fields = [
        'title',
        'slug',
        'meta_description',
        'editor__username',
        'editor__email',
        'authors__name',
        'tags__name',
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
        ('دسته‌بندی', {
            'fields': ('tags',),
            'description': 'تگ‌ها را با کاما از هم جدا کنید. مثال: جنگو, پایتون, برنامه‌نویسی'
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

    def tag_list(self, obj):
        return u", ".join(o.name for o in obj.tags.all())

    tag_list.short_description = 'لیست تگ ها'

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
        return qs.select_related('editor').prefetch_related(
            'authors',
            'tags'
        ).annotate(
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


class AdminReplyInlineForm(forms.ModelForm):
    """فرم inline برای ریپلای ادمین"""

    admin_reply_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'cols': 80,
            'placeholder': 'پاسخ شما به این کامنت...',
            'style': 'width: 100%; font-family: Tahoma, Arial; direction: rtl;'
        }),
        required=False,
        label='پاسخ ادمین'
    )

    class Meta:
        model = Comment
        fields = []


class CommentInline(admin.TabularInline):
    """Show comments in the post admin panel"""
    model = Comment
    extra = 0
    fields = ['get_author_display', 'content_preview', 'is_approved', 'is_admin_reply', 'created_at']
    readonly_fields = ['get_author_display', 'content_preview', 'created_at']
    can_delete = False

    def get_author_display(self, obj):
        if obj.is_admin_reply:
            return format_html('<strong style="color: #1976d2;">🛡️ {}</strong>',
                               obj.replied_by.get_full_name() or obj.replied_by.username)
        return obj.get_display_name()

    get_author_display.short_description = 'نویسنده'

    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content

    content_preview.short_description = 'متن'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'get_author_badge',
        'get_post_link',
        'content_preview',
        'get_status_badge',
        'get_admin_reply_badge',
        'get_replies_count',
        'created_at_jalali',
    ]

    list_filter = [
        'is_approved',
        'answered_by_admin',
        ('created_at', admin.DateFieldListFilter),
        'post',
        ('parent', admin.EmptyFieldListFilter),
    ]

    search_fields = [
        'name',
        'email',
        'content',
        'post__title',
        'ip_address',
        'admin_reply',
    ]

    readonly_fields = [
        'get_author_info',
        'ip_address',
        'created_at',
        'updated_at',
        'get_post_info',
        'get_parent_info',
        'get_replies_display',
        'admin_replied_at',
        'replied_by',
    ]

    fieldsets = (
        ('📝 اطلاعات کامنت', {
            'fields': (
                'get_post_info',
                'get_parent_info',
                'get_author_info',
                'content',
            )
        }),
        ('✅ وضعیت', {
            'fields': (
                'is_approved',
                'answered_by_admin',
            )
        }),
        ('💬 پاسخ ادمین', {
            'fields': (
                'admin_reply',
                'admin_replied_at',
                'replied_by',
            ),
            'description': 'در این بخش می‌توانید مستقیماً به کامنت کاربر پاسخ دهید. پاسخ شما در زیر کامنت اصلی نمایش داده خواهد شد.'
        }),
        ('🔐 اطلاعات امنیتی', {
            'fields': (
                'ip_address',
            ),
            'classes': ('collapse',)
        }),
        ('🕐 تاریخ و زمان', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
        ('💭 پاسخ‌های کاربران', {
            'fields': (
                'get_replies_display',
            ),
            'classes': ('collapse',)
        }),
    )

    actions = [
        'approve_comments',
        'disapprove_comments',
        'mark_as_answered',
        'mark_as_unanswered',
    ]

    list_per_page = 25
    date_hierarchy = 'created_at'

    # Display Methods 

    def get_author_badge(self, obj):
        """Show author badge"""
        if obj.is_anonymous():
            return format_html(
                '<span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
                'color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;">'
                '👤 ناشناس</span>'
            )
        else:
            return format_html(
                '<span style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); '
                'color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;">'
                '👤 {}</span>',
                obj.name
            )

    get_author_badge.short_description = 'نویسنده'

    def get_post_link(self, obj):
        """Link to post"""
        url = reverse('admin:blog_post_change', args=[obj.post.pk])
        return format_html(
            '<a href="{}" style="color: #667eea; font-weight: 600;">📄 {}</a>',
            url,
            obj.post.title[:40] + '...' if len(obj.post.title) > 40 else obj.post.title
        )

    get_post_link.short_description = 'پست'

    def content_preview(self, obj):
        """Content Preview"""
        content = obj.content[:80] + '...' if len(obj.content) > 80 else obj.content
        return format_html(
            '<div style="max-width: 300px; line-height: 1.5;">{}</div>',
            content
        )

    content_preview.short_description = 'متن کامنت'

    def get_status_badge(self, obj):
        """Show approval status"""
        if obj.is_approved:
            return format_html(
                '<span style="background: #4caf50; color: white; padding: 4px 10px; '
                'border-radius: 12px; font-size: 11px; font-weight: 600;">'
                '✅ تایید شده</span>'
            )
        else:
            return format_html(
                '<span style="background: #ff9800; color: white; padding: 4px 10px; '
                'border-radius: 12px; font-size: 11px; font-weight: 600;">'
                '⏳ در انتظار</span>'
            )

    get_status_badge.short_description = 'وضعیت'

    def get_admin_reply_badge(self, obj):
        """Show admin response status"""
        if obj.answered_by_admin and obj.admin_reply:
            return format_html(
                '<span style="background: #2196f3; color: white; padding: 4px 10px; '
                'border-radius: 12px; font-size: 11px; font-weight: 600;">'
                '✓ پاسخ داده شده</span>'
            )
        else:
            return format_html(
                '<span style="background: #ffecb3; color: #f57c00; padding: 4px 10px; '
                'border-radius: 12px; font-size: 11px; font-weight: 600;">'
                '⚠ پاسخ داده نشده</span>'
            )

    get_admin_reply_badge.short_description = 'پاسخ ادمین'

    def get_replies_count(self, obj):
        """Number of user responses"""
        count = obj.get_replies_count()
        if count > 0:
            return format_html(
                '<span style="background: #e3f2fd; color: #1976d2; padding: 3px 10px; '
                'border-radius: 10px; font-size: 12px; font-weight: 600;">'
                '💬 {}</span>',
                count
            )
        return format_html('<span style="color: #999;">-</span>')

    get_replies_count.short_description = 'پاسخ‌ها'

    def created_at_jalali(self, obj):
        return obj.created_at.strftime('%Y/%m/%d - %H:%M')

    created_at_jalali.short_description = 'تاریخ ثبت'
    created_at_jalali.admin_order_field = 'created_at'

    #  Readonly Display
    def get_author_info(self, obj):
        """Show full author information"""
        info = f'<div style="background: #f5f5f5; padding: 15px; border-radius: 8px;">'

        if obj.is_anonymous():
            info += f'<p><strong>نوع:</strong> <span style="color: #667eea;">👤 کاربر ناشناس</span></p>'
        else:
            info += f'<p><strong>نام:</strong> {obj.name}</p>'
            if obj.email:
                info += f'<p><strong>ایمیل:</strong> <a href="mailto:{obj.email}">{obj.email}</a></p>'

        info += f'<p><strong>IP:</strong> <code>{obj.ip_address}</code></p>'
        info += f'</div>'

        return format_html(info)

    get_author_info.short_description = 'اطلاعات نویسنده'

    def get_post_info(self, obj):
        """Show Post Information"""
        url = reverse('admin:blog_post_change', args=[obj.post.pk])
        view_url = obj.post.get_absolute_url() if obj.post.is_published() else None

        html = f'<div style="background: #f5f5f5; padding: 15px; border-radius: 8px;">'
        html += f'<p><strong>پست:</strong> <a href="{url}" target="_blank" style="font-size: 16px; color: #667eea;">{obj.post.title}</a></p>'
        html += f'<p><strong>تعداد کل کامنت‌ها:</strong> {obj.post.comments.filter(is_approved=True).count()}</p>'

        if view_url:
            html += f'<p><a href="{view_url}#comment-{obj.id}" target="_blank" style="color: #2196f3;">🔗 مشاهده در سایت</a></p>'

        html += f'</div>'
        return format_html(html)

    get_post_info.short_description = 'پست مربوطه'

    def get_parent_info(self, obj):
        """Show parent comment"""
        if obj.parent:
            url = reverse('admin:blog_comment_change', args=[obj.parent.pk])
            return format_html(
                '<div style="background: #e3f2fd; padding: 10px; border-radius: 6px; border-right: 3px solid #2196f3;">'
                '<p><strong>پاسخ به:</strong> <a href="{}" target="_blank">{}</a></p>'
                '<p style="margin: 5px 0 0 0; color: #666;">{}</p>'
                '</div>',
                url,
                obj.parent.get_display_name(),
                obj.parent.content[:100] + '...' if len(obj.parent.content) > 100 else obj.parent.content
            )
        return format_html('<span style="color: #999;">این یک کامنت اصلی است</span>')

    get_parent_info.short_description = 'کامنت والد'

    def get_replies_display(self, obj):
        """List of user responses"""
        replies = obj.replies.all()
        if not replies:
            return format_html('<p style="color: #999;">هیچ پاسخی از کاربران ثبت نشده است</p>')

        html = '<div style="background: #f5f5f5; padding: 15px; border-radius: 8px;">'
        for reply in replies:
            url = reverse('admin:blog_comment_change', args=[reply.pk])

            html += f'''
            <div style="background: white; padding: 10px; margin-bottom: 10px; border-radius: 6px; border-right: 3px solid #2196f3;">
                <p><strong><a href="{url}" target="_blank">{reply.get_display_name()}</a></strong> 
                <small style="color: #999;">- {reply.created_at.strftime('%Y/%m/%d %H:%M')}</small></p>
                <p style="margin: 5px 0 0 0; color: #666;">{reply.content[:150]}{'...' if len(reply.content) > 150 else ''}</p>
            </div>
            '''
        html += '</div>'

        return format_html(html)

    get_replies_display.short_description = 'پاسخ‌های کاربران'

    #  Actions
    def approve_comments(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} کامنت تایید شد.', 'success')

    approve_comments.short_description = '✅ تایید کامنت‌های انتخاب شده'

    def disapprove_comments(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} کامنت رد شد.', 'warning')

    disapprove_comments.short_description = '❌ رد کامنت‌های انتخاب شده'

    def mark_as_answered(self, request, queryset):
        updated = queryset.update(answered_by_admin=True)
        self.message_user(request, f'{updated} کامنت به عنوان "پاسخ داده شده" علامت‌گذاری شد.')

    mark_as_answered.short_description = '✓ علامت به عنوان "پاسخ داده شده"'

    def mark_as_unanswered(self, request, queryset):
        updated = queryset.update(answered_by_admin=False)
        self.message_user(request, f'{updated} کامنت به عنوان "پاسخ داده نشده" علامت‌گذاری شد.')

    mark_as_unanswered.short_description = '⚠ علامت به عنوان "نیاز به پاسخ"'

    #  Custom Save
    def save_model(self, request, obj, form, change):
        """
        Save with auto-update answered_by_admin
        """
        # Check if admin_reply is filled or not
        if 'admin_reply' in form.changed_data:
            if obj.admin_reply and obj.admin_reply.strip():
                obj.answered_by_admin = True

                if not obj.admin_replied_at:
                    obj.admin_replied_at = timezone.now()
                    obj.replied_by = request.user
            else:
                obj.answered_by_admin = False
                obj.admin_replied_at = None
                obj.replied_by = None

        super().save_model(request, obj, form, change)

    #  Query Optimization
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('post', 'parent', 'replied_by').prefetch_related('replies')

    #  Form Customization
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if 'admin_reply' in form.base_fields:
            form.base_fields['admin_reply'].widget = forms.Textarea(attrs={
                'rows': 6,
                'cols': 80,
                'style': 'width: 100%; font-family: Tahoma, Arial; direction: rtl;',
                'placeholder': 'پاسخ خود را به این کامنت بنویسید...\n\nپس از ذخیره، پاسخ شما در زیر کامنت کاربر در سایت نمایش داده خواهد شد.'
            })

        return form


class CommenterInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ("post_link", "parent_preview", "content_preview", "status_badge", "jalali_created_at")
    readonly_fields = ("post_link", "parent_preview", "content_preview", "status_badge", "jalali_created_at")
    ordering = ("-created_at",)
    show_change_link = True
    can_delete = False

    def post_link(self, obj):
        """لینک به پست"""
        if obj.post:
            return format_html(
                '<a href="/admin/blog/post/{}/change/" style="color: #0077b5; font-weight: 500;">{}</a>',
                obj.post.id,
                obj.post.title[:50]
            )
        return '—'

    post_link.short_description = 'پست'

    def parent_preview(self, obj):
        """پیش‌نمایش کامنت والد"""
        if obj.parent:
            return format_html(
                '<span style="color: #666; font-size: 12px;">پاسخ به: {}</span>',
                obj.parent.content[:30] + '...' if len(obj.parent.content) > 30 else obj.parent.content
            )
        return format_html('<span style="color: #999;">—</span>')

    parent_preview.short_description = 'پاسخ به'

    def content_preview(self, obj):
        """پیش‌نمایش محتوا"""
        preview = obj.content[:60] + '...' if len(obj.content) > 60 else obj.content
        return format_html('<span style="color: #333;">{}</span>', preview)

    content_preview.short_description = 'محتوا'

    def status_badge(self, obj):
        """وضعیت تایید"""
        if obj.is_approved:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">✓ تایید شده</span>'
            )
        return format_html(
            '<span style="background: #ffc107; color: #333; padding: 3px 10px; border-radius: 12px; font-size: 11px;">⏳ در انتظار</span>'
        )

    status_badge.short_description = 'وضعیت'

    def jalali_created_at(self, obj):
        """تاریخ شمسی"""
        return datetime2jalali(obj.created_at)

    jalali_created_at.short_description = 'تاریخ'


@admin.register(CommenterIP)
class CommenterIPAdmin(admin.ModelAdmin):
    list_display = (
        'ip_badge',
        'comments_count',
        'is_blocked',
        'status_badge',
        'last_activity',
        'jalali_created_at',
    )
    list_editable = ('is_blocked',)
    list_filter = ('is_blocked', 'created_at')

    search_fields = ('ip_address',)

    readonly_fields = (
        'ip_address',
        'created_at',
        'last_seen_at',
        'comments_count_detail',
        'last_comment_preview'
    )

    fieldsets = (
        ('اطلاعات IP', {
            'fields': ('ip_address', 'is_blocked')
        }),
        ('آمار و فعالیت', {
            'fields': ('comments_count_detail', 'last_comment_preview'),
            'classes': ('collapse',)
        }),
        ('زمان‌بندی', {
            'fields': ('created_at', 'last_seen_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [CommenterInline]

    actions = ['block_ips', 'unblock_ips']

    date_hierarchy = 'created_at'

    def ip_badge(self, obj):
        """نمایش IP با آیکون"""
        return format_html(
            '<span style="font-family: monospace; background: #f5f5f5; padding: 5px 12px; border-radius: 6px; font-size: 13px;">'
            '<i class="fas fa-network-wired" style="color: #0077b5; margin-left: 5px;"></i>{}'
            '</span>',
            obj.ip_address
        )

    ip_badge.short_description = 'آدرس IP'
    ip_badge.admin_order_field = 'ip_address'

    def comments_count(self, obj):
        """تعداد کامنت‌ها با بج رنگی"""
        count = obj.comments.count()

        if count == 0:
            color = '#999'
        elif count < 5:
            color = '#28a745'
        elif count < 10:
            color = '#ffc107'
        else:
            color = '#dc3545'

        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 12px;">{}</span>',
            color,
            count
        )

    comments_count.short_description = 'تعداد کامنت'

    def status_badge(self, obj):
        """وضعیت مسدودی"""
        if obj.is_blocked:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 5px 14px; border-radius: 6px; font-size: 12px; font-weight: 600;">'
                '<i class="fas fa-ban" style="margin-left: 5px;"></i>مسدود'
                '</span>'
            )
        return format_html(
            '<span style="background: #28a745; color: white; padding: 5px 14px; border-radius: 6px; font-size: 12px; font-weight: 600;">'
            '<i class="fas fa-check" style="margin-left: 5px;"></i>فعال'
            '</span>'
        )

    status_badge.short_description = 'وضعیت'
    status_badge.admin_order_field = 'is_blocked'

    def last_activity(self, obj):
        """آخرین فعالیت"""
        if not obj.last_seen_at:
            return format_html('<span style="color: #999;">هرگز</span>')

        # محاسبه اختلاف زمان
        now = timezone.now()
        diff = now - obj.last_seen_at

        if diff.days > 30:
            return format_html(
                '<span style="color: #999;">{} روز پیش</span>',
                diff.days
            )
        elif diff.days > 0:
            return format_html(
                '<span style="color: #666;">{} روز پیش</span>',
                diff.days
            )
        elif diff.seconds > 3600:
            return format_html(
                '<span style="color: #333;">{} ساعت پیش</span>',
                diff.seconds // 3600
            )
        else:
            return format_html(
                '<span style="color: #28a745; font-weight: 600;">همین الان</span>'
            )

    last_activity.short_description = 'آخرین فعالیت'
    last_activity.admin_order_field = 'last_seen_at'

    def jalali_created_at(self, obj):
        """تاریخ شمسی"""
        return datetime2jalali(obj.created_at)

    jalali_created_at.short_description = 'تاریخ ثبت'
    jalali_created_at.admin_order_field = 'created_at'

    def quick_actions(self, obj):
        """اکشن‌های سریع"""
        if obj.is_blocked:
            return format_html(
                '<a class="button" href="#" onclick="return confirm(\'آزاد شود؟\');" style="background: #28a745; color: white; padding: 5px 12px; border-radius: 4px; text-decoration: none; font-size: 11px;">رفع مسدودیت</a>'
            )
        return format_html(
            '<a class="button" href="#" onclick="return confirm(\'مسدود شود؟\');" style="background: #dc3545; color: white; padding: 5px 12px; border-radius: 4px; text-decoration: none; font-size: 11px;">مسدود کردن</a>'
        )

    quick_actions.short_description = 'عملیات'

    def comments_count_detail(self, obj):
        """تعداد کامنت‌ها با جزئیات"""
        total = obj.comments.count()
        approved = obj.comments.filter(is_approved=True).count()
        pending = total - approved

        return format_html(
            '<div style="line-height: 2;">'
            '<div>کل کامنت‌ها: <strong>{}</strong></div>'
            '<div style="color: #28a745;">✓ تایید شده: <strong>{}</strong></div>'
            '<div style="color: #ffc107;">⏳ در انتظار: <strong>{}</strong></div>'
            '</div>',
            total, approved, pending
        )

    comments_count_detail.short_description = 'آمار کامنت‌ها'

    def last_comment_preview(self, obj):
        """پیش‌نمایش آخرین کامنت"""
        last_comment = obj.comments.order_by('-created_at').first()

        if not last_comment:
            return format_html('<span style="color: #999;">کامنتی وجود ندارد</span>')

        return format_html(
            '<div style="background: #f8f9fa; padding: 12px; border-right: 3px solid #d8a05c; border-radius: 4px;">'
            '<div style="color: #666; font-size: 11px; margin-bottom: 5px;">{}</div>'
            '<div style="color: #333;">{}</div>'
            '</div>',
            datetime2jalali(last_comment.created_at),
            last_comment.content[:100] + '...' if len(last_comment.content) > 100 else last_comment.content
        )

    last_comment_preview.short_description = 'آخرین کامنت'

    def block_ips(self, request, queryset):
        """اکشن: مسدود کردن IPها"""
        updated = queryset.update(is_blocked=True)
        self.message_user(request, f'{updated} آی‌پی مسدود شد.', 'success')

    block_ips.short_description = '🚫 مسدود کردن IP های انتخابی'

    def unblock_ips(self, request, queryset):
        """اکشن: رفع مسدودی IPها"""
        updated = queryset.update(is_blocked=False)
        self.message_user(request, f'مسدودیت {updated} آی‌پی برداشته شد.', 'success')

    unblock_ips.short_description = '✓ رفع مسدودیت IP های انتخابی'

    def get_queryset(self, request):
        """بهینه‌سازی کوئری"""
        qs = super().get_queryset(request)
        return qs.prefetch_related('comments')

# Admin panel appearance settings
# admin.site.site_header = 'پنل مدیریت بلاگ'
# admin.site.site_title = 'ادمین بلاگ'
# admin.site.index_title = 'مدیریت محتوا'
