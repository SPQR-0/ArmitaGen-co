import csv

import jdatetime
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from jalali_date import datetime2jalali
from jalali_date.admin import ModelAdminJalaliMixin

from .models import OTP, User, UserInfo


# Helper Functions
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


class OTPExpiryFilter(admin.SimpleListFilter):
    """Custom filter for OTP expiry status"""

    title = 'وضعیت انقضا'
    parameter_name = 'expiry'

    def lookups(self, request, model_admin):
        return (
            ('active', 'فعال'),
            ('expired', 'منقضی شده'),
            ('used', 'استفاده شده'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(
                is_used=False,
                expires_at__gt=timezone.now()
            )
        if self.value() == 'expired':
            return queryset.filter(
                is_used=False,
                expires_at__lte=timezone.now()
            )
        if self.value() == 'used':
            return queryset.filter(is_used=True)
        return queryset


@admin.register(User)
class UserAdmin(ModelAdminJalaliMixin, BaseUserAdmin):
    """Custom User Admin with Jalali dates"""

    list_display = [
        'phone',
        'full_name',
        'email',
        'otp_status',
        'staff_status',
        'active_status',
        'get_jalali_date_joined',
    ]
    list_filter = [
        'is_staff',
        'is_active',
        'otp_verified',
        'date_joined',
        'last_login',
    ]
    search_fields = ['phone', 'full_name', 'email']
    ordering = ['-date_joined']

    fieldsets = (
        ('احراز هویت', {
            'fields': ('phone', 'password')
        }),
        ('اطلاعات شخصی', {
            'fields': ('full_name', 'email')
        }),
        ('دسترسی‌ها', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'otp_verified',
                'groups',
                'user_permissions',
            ),
            'classes': ('collapse',),
        }),
        ('تاریخ‌های مهم', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'full_name', 'password1', 'password2'),
        }),
    )

    readonly_fields = ['last_login', 'date_joined']

    @admin.display(description='تاریخ عضویت', ordering='date_joined')
    def get_jalali_date_joined(self, obj):
        return datetime2jalali(obj.date_joined)

    @admin.display(description='وضعیت OTP')
    def otp_status(self, obj):
        if obj.otp_verified:
            return format_html('<span style="color: green;">✓ تایید شده</span>')
        return format_html('<span style="color: red;">✗ تایید نشده</span>')

    @admin.display(description='مدیر')
    def staff_status(self, obj):
        if obj.is_staff:
            return format_html('<span style="color: blue;">⚡ مدیر</span>')
        return '—'

    @admin.display(description='وضعیت')
    def active_status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ فعال</span>')
        return format_html('<span style="color: gray;">✗ غیرفعال</span>')

    actions = ['mark_verified', 'mark_unverified', 'activate_users', 'deactivate_users']

    @admin.action(description='✓ تایید OTP کاربران انتخابی')
    def mark_verified(self, request, queryset):
        updated = queryset.update(otp_verified=True)
        self.message_user(request, f'{updated} کاربر تایید شد.')

    @admin.action(description='✗ لغو تایید OTP کاربران انتخابی')
    def mark_unverified(self, request, queryset):
        updated = queryset.update(otp_verified=False)
        self.message_user(request, f'تایید {updated} کاربر لغو شد.')

    @admin.action(description='فعال کردن کاربران انتخابی')
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} کاربر فعال شد.')

    @admin.action(description='غیرفعال کردن کاربران انتخابی')
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} کاربر غیرفعال شد.')


@admin.register(OTP)
class OTPAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    """OTP Management Admin with Jalali dates"""

    list_display = [
        'phone',
        'code_display',
        'status_badge',
        'expiry_status',
        'verified_user_link',
        'get_jalali_created_at',
    ]
    list_filter = [
        'is_used',
        'created_at',
        'expires_at',
        OTPExpiryFilter,
    ]
    search_fields = ['phone', 'code', 'verified_user__phone', 'verified_user__full_name']
    readonly_fields = [
        'code',
        'expires_at',
        'created_at',
        'time_remaining',
        'get_jalali_expires_at',
        'get_jalali_created_at_detail',
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('جزئیات OTP', {
            'fields': ('phone', 'code', 'is_used')
        }),
        ('تایید', {
            'fields': ('verified_user', 'expires_at', 'get_jalali_expires_at', 'time_remaining')
        }),
        ('زمان‌بندی', {
            'fields': ('created_at', 'get_jalali_created_at_detail'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='کد')
    def code_display(self, obj):
        return format_html(
            '<code style="background: #f4f4f4; padding: 4px 8px; border-radius: 4px; '
            'font-size: 14px; font-weight: bold;">{}</code>',
            obj.code
        )

    @admin.display(description='وضعیت')
    def status_badge(self, obj):
        if obj.is_used:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px;">استفاده شده</span>'
            )
        elif obj.is_expired():
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px;">منقضی شده</span>'
            )
        return format_html(
            '<span style="background: #ffc107; color: black; padding: 3px 10px; '
            'border-radius: 12px; font-size: 11px;">فعال</span>'
        )

    @admin.display(description='انقضا')
    def expiry_status(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">✗ منقضی شده</span>')

        remaining = obj.expires_at - timezone.now()
        minutes = int(remaining.total_seconds() / 60)

        if minutes <= 1:
            color = 'red'
        elif minutes <= 3:
            color = 'orange'
        else:
            color = 'green'

        return format_html(
            '<span style="color: {};">{} دقیقه باقی‌مانده</span>',
            color,
            minutes
        )

    @admin.display(description='کاربر تایید شده')
    def verified_user_link(self, obj):
        if obj.verified_user:
            url = f'/admin/accounts/user/{obj.verified_user.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.verified_user.full_name)
        return '—'

    @admin.display(description='تاریخ ایجاد', ordering='created_at')
    def get_jalali_created_at(self, obj):
        return datetime2jalali(obj.created_at)

    @admin.display(description='تاریخ انقضا (شمسی)')
    def get_jalali_expires_at(self, obj):
        return datetime2jalali(obj.expires_at)

    @admin.display(description='تاریخ ایجاد (شمسی)')
    def get_jalali_created_at_detail(self, obj):
        return datetime2jalali(obj.created_at)

    @admin.display(description='زمان باقی‌مانده')
    def time_remaining(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">منقضی شده</span>')

        remaining = obj.expires_at - timezone.now()
        minutes = int(remaining.total_seconds() / 60)
        seconds = int(remaining.total_seconds() % 60)

        return f"{minutes} دقیقه {seconds} ثانیه"

    actions = ['mark_as_used', 'delete_expired']

    @admin.action(description='علامت‌گذاری به عنوان استفاده شده')
    def mark_as_used(self, request, queryset):
        updated = queryset.update(is_used=True)
        self.message_user(request, f'{updated} OTP به عنوان استفاده شده علامت‌گذاری شد.')

    @admin.action(description='🗑️ حذف OTP های منقضی شده')
    def delete_expired(self, request, queryset):
        expired = queryset.filter(expires_at__lt=timezone.now())
        count = expired.count()
        expired.delete()
        self.message_user(request, f'{count} OTP منقضی شده حذف شد.')

    def has_add_permission(self, request):
        return False


@admin.register(UserInfo)
class UserInfoAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'phone',
        'email',
        'verification_badge',
        'total_reservations',
        'completed_reservations',
        'total_payments_display',
        'last_login_display',
    ]

    list_filter = [
        'is_otp_verified',
        ('last_login', admin.DateFieldListFilter),
        ('last_reservation_date', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
    ]

    search_fields = [
        'full_name',
        'phone',
        'email',
        'user__phone',
    ]

    readonly_fields = [
        'user',
        'full_name',
        'phone',
        'email',
        'is_otp_verified',
        'last_login',
        'first_reservation_date',
        'last_reservation_date',
        'total_reservations',
        'completed_reservations',
        'cancelled_reservations',
        'pending_reservations',
        'total_payments_sum',
        'successful_payments_count',
        'created_at',
        'updated_at',
        'stats_display',
    ]

    fieldsets = (
        ('اطلاعات پایه', {
            'fields': (
                'user',
                'full_name',
                'phone',
                'email',
                'is_otp_verified',
            )
        }),
        ('فعالیت', {
            'fields': (
                'last_login',
                'first_reservation_date',
                'last_reservation_date',
            )
        }),
        ('آمار رزروها', {
            'fields': (
                'total_reservations',
                'completed_reservations',
                'cancelled_reservations',
                'pending_reservations',
                'stats_display',
            )
        }),
        ('اطلاعات مالی', {
            'fields': (
                'total_payments_sum',
                'successful_payments_count',
            )
        }),
        ('تاریخچه', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    actions = [
        'export_to_csv',
        'refresh_user_stats',
        'export_active_users',
        'export_inactive_users',
        'export_top_customers',
    ]

    def verification_badge(self, obj):
        """Display verification status as badge"""
        if obj.is_otp_verified:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px;">✓ تایید شده</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; '
            'padding: 3px 10px; border-radius: 3px;">✗ تایید نشده</span>'
        )

    verification_badge.short_description = 'وضعیت OTP'

    def total_payments_display(self, obj):
        """Display total payments with formatting"""
        return f"{obj.total_payments_sum:,} تومان"

    total_payments_display.short_description = 'مجموع پرداخت‌ها'
    total_payments_display.admin_order_field = 'total_payments_sum'


    def last_login_display(self, obj):
        """Display last login with formatting"""
        if obj.last_login:
            from django.utils.timesince import timesince
            return f"{timesince(obj.last_login)} پیش"
        return "—"

    last_login_display.short_description = 'آخرین ورود'
    last_login_display.admin_order_field = 'last_login'

    def stats_display(self, obj):
        """Display comprehensive statistics"""
        return format_html(
            '<div style="line-height: 1.8;">'
            '<strong>تعداد رزروها:</strong> {}<br>'
            '<strong>رزروهای تکمیل شده:</strong> {}<br>'
            '<strong>رزروهای لغو شده:</strong> {}<br>'
            '<strong>روزهای از آخرین رزرو:</strong> {}'
            '</div>',
            obj.total_reservations,
            obj.completed_reservations,
            obj.cancelled_reservations,
            obj.days_since_last_reservation or '—'
        )

    stats_display.short_description = 'آمار کامل'

    @admin.action(description='خروجی CSV از کاربران انتخاب شده')
    def export_to_csv(self, request, queryset):
        """Export selected users to CSV with Persian dates"""
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response[
            'Content-Disposition'] = f'attachment; filename="user_info_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        response.write('\ufeff')  # UTF-8 BOM for Excel

        writer = csv.writer(response)

        writer.writerow([
            'نام و نام خانوادگی',
            'شماره تلفن',
            'ایمیل',
            'تایید شماره',
            'تعداد رزروها',
            'رزروهای تکمیل شده',
            'رزروهای لغو شده',
            'رزروهای در انتظار',
            'مجموع پرداخت‌ها (تومان)',
            'تعداد پرداخت‌های موفق',
            'آخرین ورود',
            'تاریخ اولین رزرو',
            'تاریخ آخرین رزرو',
        ])

        for obj in queryset:
            writer.writerow([
                obj.full_name,
                obj.phone,
                obj.email or '',
                'بله' if obj.is_otp_verified else 'خیر',
                obj.total_reservations,
                obj.completed_reservations,
                obj.cancelled_reservations,
                obj.pending_reservations,
                obj.total_payments_sum,
                obj.successful_payments_count,
                datetime2jalali(obj.last_login),
                date2jalali(obj.first_reservation_date.date()) if obj.first_reservation_date else '-',
                date2jalali(obj.last_reservation_date.date()) if obj.last_reservation_date else '-',
            ])

        return response

    @admin.action(description='بروزرسانی آمار کاربران انتخاب شده')
    def refresh_user_stats(self, request, queryset):
        """Refresh statistics for selected users"""
        count = 0
        for user_info in queryset:
            user_info.refresh_stats()
            count += 1

        self.message_user(
            request,
            f'آمار {count} کاربر با موفقیت بروزرسانی شد.'
        )

    @admin.action(description='خروجی CSV کاربران فعال (30 روز اخیر)')
    def export_active_users(self, request, queryset):
        """Export active users (reserved in last 30 days)"""
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        active_users = queryset.filter(
            last_reservation_date__gte=thirty_days_ago
        )
        return self.export_to_csv(request, active_users)

    @admin.action(description='خروجی CSV کاربران غیرفعال (بیش از 30 روز)')
    def export_inactive_users(self, request, queryset):
        """Export inactive users (no reservation in last 30 days)"""
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        inactive_users = queryset.filter(
            Q(last_reservation_date__lt=thirty_days_ago) |
            Q(last_reservation_date__isnull=True)
        )
        return self.export_to_csv(request, inactive_users)

    @admin.action(description='خروجی CSV برترین مشتریان (بیشترین خرید)')
    def export_top_customers(self, request, queryset):
        """Export top customers by payment amount"""
        top_customers = queryset.filter(
            total_payments_sum__gt=0
        ).order_by('-total_payments_sum')[:100]  # Top 100
        return self.export_to_csv(request, top_customers)

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')
