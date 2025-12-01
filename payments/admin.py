from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count
from django.urls import reverse

from import_export.admin import ExportActionMixin
from import_export import resources, fields

from jalali_date import datetime2jalali

from .models import Payment


# Export Resource
class PaymentResource(resources.ModelResource):
    """Export configuration for payments"""

    user_name = fields.Field(column_name='نام کاربر')
    user_phone = fields.Field(column_name='شماره تماس')
    service_name = fields.Field(column_name='نوع خدمت')
    amount_display = fields.Field(column_name='مبلغ (تومان)')
    status_display = fields.Field(column_name='وضعیت')
    created_at_jalali = fields.Field(column_name='تاریخ ایجاد')
    paid_at_jalali = fields.Field(column_name='تاریخ پرداخت')

    class Meta:
        model = Payment
        fields = (
            'id',
            'user_name',
            'user_phone',
            'service_name',
            'amount_display',
            'status_display',
            'reference_code',
            'tracking_code',
            'created_at_jalali',
            'paid_at_jalali',
        )
        export_order = fields

    def dehydrate_user_name(self, payment):
        return payment.reservation.user.full_name

    def dehydrate_user_phone(self, payment):
        return payment.reservation.user.phone

    def dehydrate_service_name(self, payment):
        return payment.reservation.service_type.name

    def dehydrate_amount_display(self, payment):
        return f"{payment.amount:,}"

    def dehydrate_status_display(self, payment):
        return payment.get_status_display()

    def dehydrate_created_at_jalali(self, payment):
        return datetime2jalali(payment.created_at).strftime('%Y/%m/%d %H:%M')

    def dehydrate_paid_at_jalali(self, payment):
        if payment.paid_at:
            return datetime2jalali(payment.paid_at).strftime('%Y/%m/%d %H:%M')
        return '-'


# Custom Filters
class PaymentStatusFilter(admin.SimpleListFilter):
    """Filter by payment status with counts"""
    title = 'وضعیت پرداخت'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        statuses = Payment.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')

        return [
            (s['status'], f"{dict(Payment.STATUS_CHOICES)[s['status']]} ({s['count']})")
            for s in statuses
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class AmountRangeFilter(admin.SimpleListFilter):
    """Filter by amount ranges"""
    title = 'محدوده مبلغ'
    parameter_name = 'amount_range'

    def lookups(self, request, model_admin):
        return [
            ('0-500000', 'کمتر از 500 هزار تومان'),
            ('500000-1000000', '500 تا 1 میلیون تومان'),
            ('1000000-2000000', '1 تا 2 میلیون تومان'),
            ('2000000+', 'بیشتر از 2 میلیون تومان'),
        ]

    def queryset(self, request, queryset):
        val = self.value()
        if val == '0-500000':
            return queryset.filter(amount__lt=500000)
        elif val == '500000-1000000':
            return queryset.filter(amount__gte=500000, amount__lt=1000000)
        elif val == '1000000-2000000':
            return queryset.filter(amount__gte=1000000, amount__lt=2000000)
        elif val == '2000000+':
            return queryset.filter(amount__gte=2000000)
        return queryset


# Main Admin
@admin.register(Payment)
class PaymentAdmin(ExportActionMixin, admin.ModelAdmin):
    """Advanced payment admin with export and statistics"""

    resource_class = PaymentResource

    list_display = [
        'id',
        'colored_status',
        'user_info',
        'service_info',
        'formatted_amount',
        'tracking_info',
        'jalali_created_at',
        'jalali_paid_at',
        'actions_column',
    ]

    list_filter = [
        PaymentStatusFilter,
        AmountRangeFilter,
        ('created_at', admin.DateFieldListFilter),
        ('paid_at', admin.DateFieldListFilter),
    ]

    search_fields = [
        'reference_code',
        'tracking_code',
        'reservation__user__phone',
        'reservation__user__full_name',
        'reservation__confirmation_code',
    ]

    readonly_fields = [
        'id',
        # 'reservation',
        'created_at',
        'paid_at',
        'colored_status_detail',
        'payment_timeline',
    ]

    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('id', 'reservation', 'amount', 'status', 'colored_status_detail')
        }),
        ('اطلاعات درگاه پرداخت', {
            'fields': ('reference_code', 'tracking_code')
        }),
        ('زمان‌بندی', {
            'fields': ('created_at', 'paid_at', 'payment_timeline')
        }),
    )

    list_per_page = 25
    date_hierarchy = 'created_at'

    actions = ['mark_as_success', 'mark_as_failed', 'mark_as_refunded']

    # -----------------------------------------------------
    # Display Methods
    # -----------------------------------------------------
    @admin.display(description='وضعیت', ordering='status')
    def colored_status(self, obj):
        colors = {
            'pending': '#FFA500',
            'success': '#28a745',
            'failed': '#dc3545',
            'refunded': '#6c757d',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#999'),
            obj.get_status_display()
        )

    @admin.display(description='کاربر')
    def user_info(self, obj):
        user = obj.reservation.user
        url = reverse('admin:accounts_user_change', args=[user.id])
        return format_html(
            '<a href="{}" style="text-decoration: none;">'
            '<strong>{}</strong><br><small style="color: #666;">{}</small></a>',
            url,
            user.full_name,
            user.phone
        )

    @admin.display(description='خدمت')
    def service_info(self, obj):
        service = obj.reservation.service_type
        price_str = f"{service.price:,}"
        return format_html(
            '<strong>{}</strong><br><small style="color: #666;">{} تومان</small>',
            service.name,
            price_str
        )

    @admin.display(description='مبلغ', ordering='amount')
    def formatted_amount(self, obj):
        amount_str = f"{obj.amount:,}"
        return format_html(
            '<strong style="color: #28a745; font-size: 14px;">{}</strong> تومان',
            amount_str
        )

    @admin.display(description='کدهای پیگیری')
    def tracking_info(self, obj):
        ref = obj.reference_code or '-'
        track = obj.tracking_code or '-'
        return format_html(
            '<small><strong>رهگیری:</strong> {}<br>'
            '<strong>پیگیری:</strong> {}</small>',
            ref[:20] + '...' if len(ref) > 20 else ref,
            track[:20] + '...' if len(track) > 20 else track
        )

    @admin.display(description='تاریخ ایجاد', ordering='created_at')
    def jalali_created_at(self, obj):
        return datetime2jalali(obj.created_at).strftime('%Y/%m/%d - %H:%M')

    @admin.display(description='تاریخ پرداخت', ordering='paid_at')
    def jalali_paid_at(self, obj):
        if obj.paid_at:
            return datetime2jalali(obj.paid_at).strftime('%Y/%m/%d - %H:%M')
        return format_html('<span style="color: #999;">-</span>')

    @admin.display(description='عملیات')
    def actions_column(self, obj):
        reservation_url = reverse('admin:council_reservation_change',
                                  args=[obj.reservation.id])
        return format_html(
            '<a href="{}" class="button" style="padding: 3px 10px;">مشاهده رزرو</a>',
            reservation_url
        )

    @admin.display(description='وضعیت جزئیات')
    def colored_status_detail(self, obj):
        STATUS_UI = {
            'success': ('✅', '#d4edda', '#155724'),
            'pending': ('⏳', '#fff3cd', '#856404'),
            'failed': ('❌', '#f8d7da', '#721c24'),
            'refunded': ('🔄', '#d6d8db', '#383d41'),
        }
        icon, bg, color = STATUS_UI.get(obj.status, ('ℹ️', '#eee', '#333'))
        return format_html(
            '<div style="background: {}; color: {}; padding: 15px; border-radius: 5px; text-align: center;">'
            '<span style="font-size: 24px;">{}</span><br>'
            '<strong style="font-size: 16px;">{}</strong></div>',
            bg, color, icon, obj.get_status_display()
        )

    @admin.display(description='تایم‌لاین پرداخت')
    def payment_timeline(self, obj):
        timeline = (
            f"<div style='background: #f8f9fa; padding: 15px; border-radius: 5px;'>"
            f"<strong>ایجاد:</strong> {datetime2jalali(obj.created_at).strftime('%Y/%m/%d %H:%M')}<br>"
        )
        if obj.paid_at:
            timeline += (
                f"<strong>پرداخت:</strong> {datetime2jalali(obj.paid_at).strftime('%Y/%m/%d %H:%M')}<br>"
            )
            delta = obj.paid_at - obj.created_at
            timeline += f"<strong>مدت زمان:</strong> {int(delta.total_seconds() / 60)} دقیقه"
        else:
            timeline += "<strong>پرداخت:</strong> <span style='color: #dc3545;'>انجام نشده</span>"
        timeline += "</div>"
        return format_html(timeline)

    # -----------------------------------------------------
    # Custom Actions
    # -----------------------------------------------------
    @admin.action(description='✅ علامت زدن به عنوان موفق')
    def mark_as_success(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status='pending').update(
            status='success',
            paid_at=timezone.now()
        )
        self.message_user(request, f'{updated} پرداخت با موفقیت به‌روزرسانی شد.')

    @admin.action(description='❌ علامت زدن به عنوان ناموفق')
    def mark_as_failed(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='failed')
        self.message_user(request, f'{updated} پرداخت به عنوان ناموفق علامت‌گذاری شد.')

    @admin.action(description='🔄 علامت زدن به عنوان بازگشت داده شده')
    def mark_as_refunded(self, request, queryset):
        updated = queryset.filter(status='success').update(status='refunded')
        self.message_user(request, f'{updated} پرداخت بازگشت داده شد.')

    # -----------------------------------------------------
    # Statistics
    # -----------------------------------------------------
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request)

        extra_context['payment_stats'] = {
            'total_count': queryset.count(),
            'total_amount': queryset.aggregate(Sum('amount'))['amount__sum'] or 0,
            'success_count': queryset.filter(status='success').count(),
            'success_amount': queryset.filter(status='success').aggregate(Sum('amount'))['amount__sum'] or 0,
            'pending_count': queryset.filter(status='pending').count(),
            'failed_count': queryset.filter(status='failed').count(),
        }

        return super().changelist_view(request, extra_context)

    class Media:
        css = {
            'all': ('admin/css/custom_payment_admin.css',)
        }
