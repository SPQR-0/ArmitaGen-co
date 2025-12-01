from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
from django.urls import reverse
from import_export.admin import ExportActionMixin
from import_export import resources, fields
from jalali_date import datetime2jalali
from .models import Report


# Resource for Export
class ReportResource(resources.ModelResource):
    """Export configuration for reports"""

    creator_name = fields.Field(column_name='نام ایجادکننده')
    type_display = fields.Field(column_name='نوع گزارش')
    visibility = fields.Field(column_name='نمایش به کاربر')
    created_at_jalali = fields.Field(column_name='تاریخ ایجاد')

    class Meta:
        model = Report
        fields = (
            'id',
            'type_display',
            'related_id',
            'title',
            'content',
            'creator_name',
            'visibility',
            'created_at_jalali',
        )

    def dehydrate_creator_name(self, report):
        return report.created_by.full_name

    def dehydrate_type_display(self, report):
        return report.get_type_display()

    def dehydrate_visibility(self, report):
        return 'بله' if report.is_visible_to_user else 'خیر'

    def dehydrate_created_at_jalali(self, report):
        return datetime2jalali(report.created_at).strftime('%Y/%m/%d %H:%M')


# Custom Filters
class ReportTypeFilter(admin.SimpleListFilter):
    title = 'نوع گزارش'
    parameter_name = 'type'

    def lookups(self, request, model_admin):
        types = Report.objects.values('type').annotate(count=Count('id')).order_by('type')
        return [
            (t['type'], f"{dict(Report.TYPE_CHOICES)[t['type']]} ({t['count']})")
            for t in types
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(type=self.value())
        return queryset


class VisibilityFilter(admin.SimpleListFilter):
    title = 'نمایش به کاربر'
    parameter_name = 'visibility'

    def lookups(self, request, model_admin):
        return [
            ('visible', 'قابل مشاهده'),
            ('hidden', 'مخفی'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'visible':
            return queryset.filter(is_visible_to_user=True)
        elif self.value() == 'hidden':
            return queryset.filter(is_visible_to_user=False)
        return queryset


@admin.register(Report)
class ReportAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class = ReportResource

    list_display = [
        'id',
        'colored_type',
        'title_display',
        'creator_info',
        'related_entity',
        'visibility_badge',
        'jalali_created_at',
        'actions_column',
    ]

    list_filter = [
        ReportTypeFilter,
        VisibilityFilter,
        ('created_at', admin.DateFieldListFilter),
        'created_by',
    ]

    search_fields = [
        'title',
        'content',
        'created_by__full_name',
        'related_id',
    ]

    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'report_preview',
    ]

    fieldsets = (
        ('اطلاعات اصلی', {'fields': ('id', 'type', 'related_id', 'title')}),
        ('محتوای گزارش', {'fields': ('content', 'report_preview'), 'classes': ('wide',)}),
        ('تنظیمات', {'fields': ('created_by', 'is_visible_to_user')}),
        ('زمان‌بندی', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    list_per_page = 20
    date_hierarchy = 'created_at'

    actions = ['make_visible', 'make_hidden', 'duplicate_report']

    @admin.display(description='نوع', ordering='type')
    def colored_type(self, obj):
        colors = {'reservation': '#007bff', 'user': '#28a745', 'payment': '#ffc107', 'system': '#dc3545'}
        icons = {'reservation': '📅', 'user': '👤', 'payment': '💳', 'system': '⚙️'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{} {}</span>',
            colors.get(obj.type, '#999'),
            icons.get(obj.type, '📄'),
            obj.get_type_display()
        )

    @admin.display(description='عنوان', ordering='title')
    def title_display(self, obj):
        title = obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
        return format_html('<strong>{}</strong>', title)

    @admin.display(description='ایجادکننده')
    def creator_info(self, obj):
        user = obj.created_by
        url = reverse('admin:accounts_user_change', args=[user.id])

        badge_html = ''
        if user.is_staff:
            badge_html = format_html(
                '<span style="background: #dc3545; color: white; padding: 2px 5px; '
                'border-radius: 3px; font-size: 10px; margin-left: 5px;">ADMIN</span>'
            )

        return format_html(
            '{}<a href="{}" style="text-decoration: none;"><strong>{}</strong></a>',
            badge_html,
            url,
            user.full_name
        )

    @admin.display(description='مرتبط با')
    def related_entity(self, obj):
        if not obj.related_id:
            return format_html('<span style="color: #999;">-</span>')

        url = None
        if obj.type == 'reservation':
            url = reverse('admin:council_reservation_change', args=[obj.related_id])
        elif obj.type == 'payment':
            url = reverse('admin:payments_payment_change', args=[obj.related_id])
        elif obj.type == 'user':
            url = reverse('admin:accounts_user_change', args=[obj.related_id])

        if url:
            return format_html('<a href="{}" class="button" style="padding: 3px 10px;">مشاهده #{}</a>', url, obj.related_id)

        return f'#{obj.related_id}'

    @admin.display(description='نمایش')
    def visibility_badge(self, obj):
        if obj.is_visible_to_user:
            return format_html('<span style="color: #28a745; font-size: 18px;" title="قابل مشاهده">👁️</span>')
        return format_html('<span style="color: #dc3545; font-size: 18px;" title="مخفی">🚫</span>')

    @admin.display(description='تاریخ ایجاد', ordering='created_at')
    def jalali_created_at(self, obj):
        return datetime2jalali(obj.created_at).strftime('%Y/%m/%d - %H:%M')

    @admin.display(description='عملیات')
    def actions_column(self, obj):
        buttons = []
        buttons.append(f'<a href="#" class="button" style="padding: 3px 10px; background: #007bff; color: white;">مشاهده</a>')
        action = 'مخفی کردن' if obj.is_visible_to_user else 'نمایش'
        color = '#dc3545' if obj.is_visible_to_user else '#28a745'
        buttons.append(f'<a href="#" class="button" style="padding: 3px 10px; background: {color}; color: white;">{action}</a>')
        return format_html(' '.join(buttons))

    @admin.display(description='پیش‌نمایش گزارش')
    def report_preview(self, obj):
        content = obj.content[:500] + '...' if len(obj.content) > 500 else obj.content
        return format_html('<div style="background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff; white-space: pre-wrap;">{}</div>', content)

    # Actions
    @admin.action(description='👁️ قابل مشاهده کردن برای کاربران')
    def make_visible(self, request, queryset):
        updated = queryset.update(is_visible_to_user=True)
        self.message_user(request, f'{updated} گزارش برای کاربران قابل مشاهده شد.')

    @admin.action(description='🚫 مخفی کردن از کاربران')
    def make_hidden(self, request, queryset):
        updated = queryset.update(is_visible_to_user=False)
        self.message_user(request, f'{updated} گزارش از کاربران مخفی شد.')

    @admin.action(description='📋 کپی کردن گزارش')
    def duplicate_report(self, request, queryset):
        for report in queryset:
            report.pk = None
            report.title = f"کپی - {report.title}"
            report.created_by = request.user
            report.save()
        self.message_user(request, f'{queryset.count()} گزارش کپی شد.')

    # Statistics
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request)

        stats = {
            'total_count': queryset.count(),
            'visible_count': queryset.filter(is_visible_to_user=True).count(),
            'by_type': {
                dict(Report.TYPE_CHOICES)[t['type']]: t['count']
                for t in queryset.values('type').annotate(count=Count('id'))
            },
        }
        extra_context['report_stats'] = stats
        return super().changelist_view(request, extra_context)
