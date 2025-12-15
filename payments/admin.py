import csv

import jdatetime
from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.contrib.admin import SimpleListFilter
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

from council.utils.export_utils import export_to_csv
from .models import Payment


class PaidDateFilter(SimpleListFilter):
    title = 'تاریخ پرداخت'
    parameter_name = 'paid_at'

    def lookups(self, request, model_admin):
        return (
            ('today', 'امروز'),
            ('yesterday', 'دیروز'),
            ('last_7_days', '7 روز گذشته'),
            ('this_month', 'این ماه'),
        )

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(paid_at__date=today)
        elif self.value() == 'yesterday':
            return queryset.filter(paid_at__date=today - timezone.timedelta(days=1))
        elif self.value() == 'last_7_days':
            return queryset.filter(paid_at__date__gte=today - timezone.timedelta(days=7))
        elif self.value() == 'this_month':
            return queryset.filter(paid_at__year=today.year, paid_at__month=today.month)
        return queryset


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin panel for payment management"""

    list_display = [
        'id',
        'reservation_info',
        'amount_display',
        'status_badge',
        'tracking_code',
        'paid_at_jalali',
        'created_at_jalali'
    ]

    readonly_fields = [
        'reservation',
        'amount',
        'tracking_code',
        'paid_at_jalali',
        'created_at_jalali'
    ]

    list_filter = [
        'status',
        ('created_at', DateFieldListFilter),
        PaidDateFilter,
    ]
    search_fields = [
        'reservation__tracking_code',
        'reservation__phone_number',
        'reservation__full_name',
        'tracking_code'
    ]

    date_hierarchy = 'created_at'
    actions = ['mark_as_refunded', 'export_payment_report', 'export_payments_csv_jalali']

    fieldsets = (
        ('اطلاعات پرداخت', {
            'fields': ('reservation', 'amount', 'status')
        }),
        ('زمان‌بندی', {
            'fields': ('paid_at',),
            'classes': ('collapse',)
        }),
    )

    @admin.action(description='📥 خروجی CSV کامل پرداخت‌ها')
    def export_payments_csv_jalali(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename=payments_full.csv'

        writer = csv.writer(response, delimiter=',', quoting=csv.QUOTE_MINIMAL)

        # Header CSV
        writer.writerow([
            'شناسه',
            'رزرو',
            'نام و نام خانوادگی',
            'شماره تماس',
            'کد پیگیری رزرو',
            'نوع مشاوره',
            'عنوان مشاوره',
            'وضعیت پرداخت',
            'مبلغ (تومان)',
            'تاریخ و زمان پرداخت',
            'تاریخ و زمان ایجاد پرداخت',
            'تاریخ و زمان رزرو نوبت'
        ])

        def jalali_date(dt):
            if not dt:
                return '-'
            return jdatetime.datetime.fromgregorian(datetime=dt).strftime('%Y/%m/%d %H:%M:%S')

        for payment in queryset:
            reservation = payment.reservation
            service_type = reservation.service_type.name if reservation.service_type else '-'
            consultation_topic = reservation.consultation_topic.name if reservation.consultation_topic else '-'

            writer.writerow([
                payment.id,
                reservation.tracking_code if reservation else '-',
                reservation.full_name if reservation else '-',
                reservation.phone_number if reservation else '-',
                reservation.tracking_code if reservation else '-',
                service_type,
                consultation_topic,
                payment.get_status_display(),
                payment.amount,
                jalali_date(payment.paid_at),
                jalali_date(payment.created_at),
                jalali_date(reservation.reserved_at) if reservation else '-',
            ])

        return response

    def paid_at_jalali(self, obj):
        if obj.paid_at:
            return jdatetime.datetime.fromgregorian(datetime=obj.paid_at).strftime('%Y/%m/%d %H:%M')
        return '-'

    paid_at_jalali.short_description = 'تاریخ پرداخت'
    paid_at_jalali.admin_order_field = 'paid_at'

    def created_at_jalali(self, obj):
        return jdatetime.datetime.fromgregorian(datetime=obj.created_at).strftime('%Y/%m/%d %H:%M')

    created_at_jalali.short_description = 'تاریخ ایجاد'
    created_at_jalali.admin_order_field = 'created_at'

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
    amount_display.admin_order_field = 'amount'

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

    @admin.action(description='📊 گزارش کامل پرداخت‌ها')
    def export_payment_report(self, request, queryset):
        total_payments = queryset.count()
        successful_payments = queryset.filter(status='success').count()
        pending_payments = queryset.filter(status='pending').count()
        failed_payments = queryset.filter(status='failed').count()
        refunded_payments = queryset.filter(status='refunded').count()

        total_amount = queryset.filter(status='success').aggregate(
            Sum('amount')
        )['amount__sum'] or 0

        refunded_amount = queryset.filter(status='refunded').aggregate(
            Sum('amount')
        )['amount__sum'] or 0

        message = (
            f"📊 گزارش پرداخت‌ها:\n"
            f"تعداد کل پرداخت‌ها: {total_payments}\n | "
            f"پرداخت‌های موفق: {successful_payments}\n | "
            f"پرداخت‌های در انتظار: {pending_payments}\n | "
            f"پرداخت‌های ناموفق: {failed_payments}\n | "
            f"پرداخت‌های بازگشت داده شده: {refunded_payments}\n | "
            f"مجموع مبلغ پرداخت موفق: {total_amount:,} تومان\n | "
            f"مجموع مبلغ بازگشت داده شده: {refunded_amount:,} تومان"
        )

        self.message_user(request, message, level='info')


    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj=obj)
