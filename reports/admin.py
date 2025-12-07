from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Admin panel for report management"""

    list_display = [
        'id',
        'type_badge',
        'title',
        'related_object_link',
        'created_by',
        'visibility_badge',
        'created_at'
    ]
    list_filter = [
        'type',
        'is_visible_to_user',
        'created_at',
        'created_by'
    ]
    search_fields = [
        'title',
        'content',
        'related_id',
        'created_by__full_name',
        'created_by__phone'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    list_per_page = 50

    fieldsets = (
        ('اطلاعات گزارش', {
            'fields': ('type', 'title', 'content')
        }),
        ('ارتباط', {
            'fields': ('related_id',),
            'description': 'شناسه رکورد مرتبط (مثلاً ID رزرو، کاربر یا پرداخت)'
        }),
        ('دسترسی', {
            'fields': ('created_by', 'is_visible_to_user')
        }),
        ('اطلاعات سیستمی', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def type_badge(self, obj):
        """Display report type with colored badge"""
        colors = {
            'reservation': '#007bff',
            'user': '#28a745',
            'payment': '#ffc107',
            'system': '#6c757d',
        }
        icons = {
            'reservation': '📋',
            'user': '👤',
            'payment': '💳',
            'system': '⚙️',
        }
        color = colors.get(obj.type, '#6c757d')
        icon = icons.get(obj.type, '📄')

        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; '
            'border-radius: 10px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_type_display()
        )

    type_badge.short_description = 'نوع'

    def related_object_link(self, obj):
        """Display link to related object if available"""
        if not obj.related_id:
            return format_html('<span style="color: #6c757d;">-</span>')

        related = obj.get_related_object()
        if not related:
            return format_html(
                '<span style="color: #dc3545;">ID: {} (یافت نشد)</span>',
                obj.related_id
            )

        # Generate appropriate admin URL based on type
        url_mapping = {
            'reservation': f'/admin/council/reservation/{obj.related_id}/change/',
            'user': f'/admin/accounts/user/{obj.related_id}/change/',
            'payment': f'/admin/payments/payment/{obj.related_id}/change/',
        }

        url = url_mapping.get(obj.type)
        if url:
            return format_html(
                '<a href="{}" style="font-weight: bold;">مشاهده {}</a>',
                url,
                obj.get_type_display()
            )

        return format_html('<span>ID: {}</span>', obj.related_id)

    related_object_link.short_description = 'مرتبط با'

    def visibility_badge(self, obj):
        """Display visibility status"""
        if obj.is_visible_to_user:
            return format_html(
                '<span style="color: #28a745; font-size: 16px;" '
                'title="کاربر می‌تواند این گزارش را ببیند">👁️ عمومی</span>'
            )
        return format_html(
            '<span style="color: #6c757d; font-size: 16px;" '
            'title="فقط ادمین می‌تواند این گزارش را ببیند">🔒 خصوصی</span>'
        )

    visibility_badge.short_description = 'دسترسی'

    def save_model(self, request, obj, form, change):
        """Auto-set created_by on new reports"""
        if not change:  # Only on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        """Add summary statistics to changelist"""
        extra_context = extra_context or {}

        # Calculate statistics
        queryset = self.get_queryset(request)

        stats = {
            'total_reports': queryset.count(),
            'by_type': queryset.values('type').annotate(
                count=Count('id')
            ).order_by('-count'),
            'visible_to_users': queryset.filter(is_visible_to_user=True).count(),
            'private_reports': queryset.filter(is_visible_to_user=False).count(),
        }

        extra_context['report_stats'] = stats

        return super().changelist_view(request, extra_context)

    def get_readonly_fields(self, request, obj=None):
        """Make created_by readonly when editing"""
        if obj:  # Editing existing report
            return self.readonly_fields + ['created_by']
        return self.readonly_fields