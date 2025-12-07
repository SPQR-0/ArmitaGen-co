from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html

from council.utils.export_utils import export_to_csv
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin panel for payment management"""

    list_display = [
        'id',
        'reservation_info',
        'amount_display',
        'status_badge',
        'tracking_code',
        'paid_at',
        'created_at'
    ]
    list_filter = [
        'status',
        'created_at',
        'paid_at'
    ]
    search_fields = [
        'reservation__tracking_code',
        'reservation__phone_number',
        'reservation__full_name',
        'tracking_code'
    ]
    readonly_fields = [
        'reservation',
        'amount',
        'tracking_code',
        'paid_at',
        'created_at'
    ]
    date_hierarchy = 'created_at'
    actions = ['mark_as_refunded', 'export_payment_report', 'export_payments_csv']

    fieldsets = (
        ('اطلاعات پرداخت', {
            'fields': ('reservation', 'amount', 'status')
        }),
        ('زمان‌بندی', {
            'fields': ('paid_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def reservation_info(self, obj):
        url = f'/admin/council/reservation/{obj.reservation.id}/change/'
        return format_html(
            '<a href="{}" style="font-weight: bold;">{}</a><br/>'
            '<small style="color: #6c757d;">{}</small>',
            url,
            obj.reservation.tracking_code,
            obj.reservation.full_name
        )

    reservation_info.short_description = 'رزرو'

    def amount_display(self, obj):
        formatted = f"{obj.amount:,}"
        return format_html(
            '<strong style="color: #28a745; font-size: 13px;">{}</strong> '
            '<small style="color: #6c757d;">تومان</small>',
            formatted
        )

    amount_display.short_description = 'مبلغ'

    def status_badge(self, obj):
        colors = {
            'pending': '#FFC107',
            'success': '#28a745',
            'failed': '#dc3545',
            'refunded': '#6c757d',
        }
        icons = {
            'pending': '⏳',
            'success': '✓',
            'failed': '✗',
            'refunded': '↩',
        }
        color = colors.get(obj.status, '#6c757d')
        icon = icons.get(obj.status, '?')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_status_display()
        )

    status_badge.short_description = 'وضعیت'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request)

        stats = {
            'total_payments': queryset.count(),
            'successful_payments': queryset.filter(status='success').count(),
            'pending_payments': queryset.filter(status='pending').count(),
            'failed_payments': queryset.filter(status='failed').count(),
            'refunded_payments': queryset.filter(status='refunded').count(),
            'total_amount': queryset.filter(status='success').aggregate(
                Sum('amount')
            )['amount__sum'] or 0,
            'refunded_amount': queryset.filter(status='refunded').aggregate(
                Sum('amount')
            )['amount__sum'] or 0,
        }

        extra_context['payment_stats'] = stats
        return super().changelist_view(request, extra_context)

    def mark_as_refunded(self, request, queryset):
        refundable = queryset.filter(status='success')
        updated = refundable.update(status='refunded')

        for payment in refundable:
            payment.reservation.payment_status = 'refunded'
            payment.reservation.save(update_fields=['payment_status'])

        self.message_user(
            request,
            f'{updated} پرداخت به عنوان بازگشت داده شده علامت‌گذاری شد.'
        )

        if updated < queryset.count():
            self.message_user(
                request,
                'فقط پرداخت‌های موفق می‌توانند بازگشت داده شوند.',
                level='warning'
            )

    mark_as_refunded.short_description = 'بازگشت وجه'

    def export_payment_report(self, request, queryset):
        total_amount = queryset.filter(status='success').aggregate(
            Sum('amount')
        )['amount__sum'] or 0

        self.message_user(
            request,
            f'گزارش {queryset.count()} پرداخت با مجموع '
            f'{total_amount:,} تومان آماده است. این قابلیت به زودی اضافه خواهد شد.',
            level='info'
        )

    export_payment_report.short_description = 'خروجی گزارش پرداخت'

    @admin.action(description='📥 خروجی CSV پرداخت‌ها')
    def export_payments_csv(self, request, queryset):
        """Export payments to CSV"""
        fields = [
            'id',
            'reservation',
            'amount',
            'status',
            'reference_code',
            'tracking_code',
            'paid_at',
            'created_at',
        ]
        return export_to_csv(queryset, 'payments', fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj=obj)
