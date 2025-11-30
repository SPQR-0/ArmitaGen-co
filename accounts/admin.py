from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html

from .models import User, OTP


class OTPExpiryFilter(admin.SimpleListFilter):
    """Custom filter for OTP expiry status"""

    title = 'expiry status'
    parameter_name = 'expiry'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('used', 'Used'),
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
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""

    list_display = [
        'phone',
        'full_name',
        'email',
        'otp_status',
        'staff_status',
        'active_status',
        'date_joined',
    ]
    list_filter = [
        'is_staff',
        'is_active',
        'otp_verified',
        'date_joined',
    ]
    search_fields = ['phone', 'full_name', 'email']
    ordering = ['-date_joined']

    fieldsets = (
        ('Authentication', {
            'fields': ('phone', 'password')
        }),
        ('Personal Info', {
            'fields': ('full_name', 'email')
        }),
        ('Permissions', {
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
        ('Important Dates', {
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

    def otp_status(self, obj):
        if obj.otp_verified:
            return format_html(
                '<span style="color: green;">✓ Verified</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Not Verified</span>'
        )

    otp_status.short_description = 'OTP Status'

    def staff_status(self, obj):
        if obj.is_staff:
            return format_html(
                '<span style="color: blue;">⚡ Staff</span>'
            )
        return '—'

    staff_status.short_description = 'Staff'

    def active_status(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green;">✓ Active</span>'
            )
        return format_html(
            '<span style="color: gray;">✗ Inactive</span>'
        )

    active_status.short_description = 'Status'

    actions = ['mark_verified', 'mark_unverified', 'activate_users', 'deactivate_users']

    def mark_verified(self, request, queryset):
        updated = queryset.update(otp_verified=True)
        self.message_user(request, f'{updated} users marked as verified.')

    mark_verified.short_description = 'Mark selected as OTP verified'

    def mark_unverified(self, request, queryset):
        updated = queryset.update(otp_verified=False)
        self.message_user(request, f'{updated} users marked as unverified.')

    mark_unverified.short_description = 'Mark selected as OTP unverified'

    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users activated.')

    activate_users.short_description = 'Activate selected users'

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users deactivated.')

    deactivate_users.short_description = 'Deactivate selected users'


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    """OTP Management Admin"""

    list_display = [
        'phone',
        'code_display',
        'status_badge',
        'expiry_status',
        'verified_user_link',
        'created_at',
    ]
    list_filter = [
        'is_used',
        'created_at',
        OTPExpiryFilter,
    ]
    search_fields = ['phone', 'code', 'verified_user__phone', 'verified_user__full_name']
    readonly_fields = [
        'code',
        'expires_at',
        'created_at',
        'time_remaining',
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('OTP Details', {
            'fields': ('phone', 'code', 'is_used')
        }),
        ('Verification', {
            'fields': ('verified_user', 'expires_at', 'time_remaining')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def code_display(self, obj):
        return format_html(
            '<code style="background: #f4f4f4; padding: 4px 8px; border-radius: 4px; font-size: 14px;">{}</code>',
            obj.code
        )

    code_display.short_description = 'Code'

    def status_badge(self, obj):
        if obj.is_used:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">USED</span>'
            )
        elif obj.is_expired():
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">EXPIRED</span>'
            )
        return format_html(
            '<span style="background: #ffc107; color: black; padding: 3px 10px; border-radius: 12px; font-size: 11px;">ACTIVE</span>'
        )

    status_badge.short_description = 'Status'

    def expiry_status(self, obj):
        if obj.is_expired():
            return format_html(
                '<span style="color: red;">✗ Expired</span>'
            )

        remaining = obj.expires_at - timezone.now()
        minutes = int(remaining.total_seconds() / 60)

        if minutes <= 1:
            color = 'red'
        elif minutes <= 3:
            color = 'orange'
        else:
            color = 'green'

        return format_html(
            '<span style="color: {};">{} min left</span>',
            color,
            minutes
        )

    expiry_status.short_description = 'Expiry'

    def verified_user_link(self, obj):
        if obj.verified_user:
            url = f'/admin/accounts/user/{obj.verified_user.id}/change/'
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.verified_user.full_name
            )
        return '—'

    verified_user_link.short_description = 'Verified User'

    def time_remaining(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">Expired</span>')

        remaining = obj.expires_at - timezone.now()
        minutes = int(remaining.total_seconds() / 60)
        seconds = int(remaining.total_seconds() % 60)

        return f"{minutes}m {seconds}s"

    time_remaining.short_description = 'Time Remaining'

    actions = ['mark_as_used', 'delete_expired']

    def mark_as_used(self, request, queryset):
        updated = queryset.update(is_used=True)
        self.message_user(request, f'{updated} OTPs marked as used.')

    mark_as_used.short_description = 'Mark selected as used'

    def delete_expired(self, request, queryset):
        expired = queryset.filter(expires_at__lt=timezone.now())
        count = expired.count()
        expired.delete()
        self.message_user(request, f'{count} expired OTPs deleted.')

    delete_expired.short_description = 'Delete expired OTPs'

    def has_add_permission(self, request):
        # Prevent manual OTP creation
        return False


class OTPExpiryFilter(admin.SimpleListFilter):
    """Custom filter for OTP expiry status"""

    title = 'expiry status'
    parameter_name = 'expiry'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('used', 'Used'),
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
