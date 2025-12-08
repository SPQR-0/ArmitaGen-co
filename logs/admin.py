from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from jalali_date import datetime2jalali
from jalali_date.admin import ModelAdminJalaliMixin
import json

from .models import (
    UserActivity, UserStatistics, ReservationLog,
    PaymentLog, ErrorLog
)


@admin.register(UserActivity)
class UserActivityAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    """
    Comprehensive user activity admin
    """

    list_display = [
        'id',
        'user_display',
        'action_badge',
        'severity_badge',
        'description_short',
        'device_info',
        'ip_display',
        'get_jalali_created_at'
    ]

    list_filter = [
        'action_type',
        'severity',
        'device_type',
        'browser',
        'os',
        'created_at'
    ]

    search_fields = [
        'user__full_name',
        'user__phone',
        'description',
        'ip_address',
        'session_key'
    ]

    readonly_fields = [
        'user',
        'session_key',
        'action_type',
        'severity',
        'description',
        'content_type',
        'object_id',
        'metadata_display',
        'ip_address',
        'user_agent',
        'device_type',
        'browser',
        'os',
        'created_at',
        'get_jalali_created_at'
    ]

    date_hierarchy = 'created_at'
    list_per_page = 50

    fieldsets = (
        ('اطلاعات کاربر', {
            'fields': ('user', 'session_key')
        }),
        ('جزئیات عملیات', {
            'fields': ('action_type', 'severity', 'description', 'content_type', 'object_id')
        }),
        ('اطلاعات درخواست', {
            'fields': ('ip_address', 'user_agent', 'device_type', 'browser', 'os'),
            'classes': ('collapse',)
        }),
        ('داده‌های اضافی', {
            'fields': ('metadata_display',),
            'classes': ('collapse',)
        }),
        ('زمان', {
            'fields': ('created_at', 'get_jalali_created_at')
        })
    )

    def user_display(self, obj):
        """Display user with link"""
        if obj.user:
            url = f'/admin/accounts/user/{obj.user.id}/change/'
            return format_html(
                '<a href="{}" style="font-weight: bold;">{}</a><br/>'
                '<small style="color: #6b7280;">{}</small>',
                url,
                obj.user.full_name,
                obj.user.phone
            )
        return format_html(
            '<span style="color: #9ca3af;">Guest</span><br/>'
            '<small style="color: #d1d5db;">{}</small>',
            obj.session_key[:10] if obj.session_key else '-'
        )

    user_display.short_description = 'کاربر'

    def action_badge(self, obj):
        """Display action type with icon"""
        icons = {
            'registration': '📝',
            'login': '🔑',
            'logout': '🚪',
            'otp_request': '📱',
            'otp_verify': '✅',
            'reservation_start': '📅',
            'reservation_created': '✓',
            'reservation_cancelled': '❌',
            'payment_init': '💳',
            'payment_success': '💰',
            'payment_failed': '⚠️',
            'file_upload': '📎',
            'pdf_download': '📄',
        }
        icon = icons.get(obj.action_type, '📊')

        colors = {
            'login': '#10b981',
            'registration': '#3b82f6',
            'payment_success': '#059669',
            'payment_failed': '#ef4444',
            'reservation_cancelled': '#f59e0b',
        }
        color = colors.get(obj.action_type, '#6b7280')

        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; '
            'border-radius: 8px; font-size: 11px; font-weight: 600;">'
            '{} {}</span>',
            color,
            icon,
            obj.get_action_type_display()
        )

    action_badge.short_description = 'عملیات'

    def severity_badge(self, obj):
        """Display severity level"""
        colors = {
            'info': '#3b82f6',
            'warning': '#f59e0b',
            'error': '#ef4444',
            'critical': '#dc2626'
        }
        icons = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🔥'
        }

        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 6px; font-size: 10px;">{} {}</span>',
            colors.get(obj.severity, '#6b7280'),
            icons.get(obj.severity, 'ℹ️'),
            obj.get_severity_display()
        )

    severity_badge.short_description = 'سطح'

    def description_short(self, obj):
        """Truncated description"""
        if len(obj.description) > 60:
            return obj.description[:60] + '...'
        return obj.description

    description_short.short_description = 'توضیحات'

    def device_info(self, obj):
        """Display device and browser info"""
        if obj.device_type or obj.browser:
            return format_html(
                '<strong>{}</strong><br/>'
                '<small style="color: #6b7280;">{} - {}</small>',
                obj.device_type or '-',
                obj.browser or '-',
                obj.os or '-'
            )
        return '-'

    device_info.short_description = 'دستگاه'

    def ip_display(self, obj):
        """Display IP address"""
        if obj.ip_address:
            return format_html(
                '<code style="background: #f3f4f6; padding: 3px 8px; '
                'border-radius: 4px; font-size: 11px;">{}</code>',
                obj.ip_address
            )
        return '-'

    ip_display.short_description = 'IP'

    def metadata_display(self, obj):
        """Display metadata as formatted JSON"""
        if obj.metadata:
            try:
                formatted = json.dumps(obj.metadata, indent=2, ensure_ascii=False)
                return format_html(
                    '<pre style="background: #f9fafb; padding: 10px; '
                    'border-radius: 5px; font-size: 12px; max-width: 600px; '
                    'overflow-x: auto;">{}</pre>',
                    formatted
                )
            except:
                return str(obj.metadata)
        return '-'

    metadata_display.short_description = 'داده‌های اضافی'

    @admin.display(description='تاریخ (شمسی)', ordering='created_at')
    def get_jalali_created_at(self, obj):
        return datetime2jalali(obj.created_at).strftime('%Y/%m/%d - %H:%M:%S')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False