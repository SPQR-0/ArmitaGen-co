from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html
from jalali_date import datetime2jalali
from jalali_date.admin import ModelAdminJalaliMixin

from .models import User, OTP


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
        return datetime2jalali(obj.date_joined).strftime('%Y/%m/%d - %H:%M')

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
        return datetime2jalali(obj.created_at).strftime('%Y/%m/%d - %H:%M')

    @admin.display(description='تاریخ انقضا (شمسی)')
    def get_jalali_expires_at(self, obj):
        return datetime2jalali(obj.expires_at).strftime('%Y/%m/%d - %H:%M:%S')

    @admin.display(description='تاریخ ایجاد (شمسی)')
    def get_jalali_created_at_detail(self, obj):
        return datetime2jalali(obj.created_at).strftime('%Y/%m/%d - %H:%M:%S')

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
