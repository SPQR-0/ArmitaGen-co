import csv
from datetime import date, datetime, timedelta

import jdatetime
import pytz
from django import forms
from django.contrib import admin, messages
from django.db import models
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from jalali_date.admin import ModelAdminJalaliMixin
from jalali_date.fields import JalaliDateField, SplitJalaliDateTimeField
from jalali_date.widgets import AdminJalaliDateWidget, AdminSplitJalaliDateTime

from council.admin_utils.csv import safe_csv
from council.utils.export_utils import export_to_csv
from council.utils.pdf_generator import generate_admin_receipt_pdf, generate_user_receipt_pdf
from council.utils.reservation_expiration import mark_expired_time_slots
from .admin_filters import JalaliDateRangeFilter
from .models import (ConsultationTopic, Reservation, ServiceType, SlotRule,
                     TimeSlot)


# Helper Function
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


class TimeSlotJalaliDateFilter(admin.SimpleListFilter):
    title = 'تاریخ (شمسی)'
    parameter_name = 'jalali_date'

    def lookups(self, request, model_admin):
        dates = (
            TimeSlot.objects
            .values_list('date', flat=True)
            .distinct()
            .order_by('date')
        )

        jalali_dates = []
        for d in dates:
            if d:
                j = jdatetime.date.fromgregorian(date=d)
                jalali_dates.append((d, j.strftime('%Y/%m/%d')))
        return jalali_dates

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(date=value)
        return queryset


class JalaliDateFilter(admin.SimpleListFilter):
    title = 'تاریخ نوبت (شمسی)'
    parameter_name = 'jalali_date'

    def lookups(self, request, model_admin):
        dates = (
            Reservation.objects
            .values_list('time_slot__date', flat=True)
            .distinct()
            .order_by('time_slot__date')
        )

        jalali_dates = []
        for d in dates:
            if d:
                j = jdatetime.date.fromgregorian(date=d)
                jalali_dates.append((d, j.strftime('%Y/%m/%d')))
        return jalali_dates

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(time_slot__date=value)
        return queryset


class HasReservationFilter(admin.SimpleListFilter):
    title = 'رزرو کننده'
    parameter_name = 'has_reservation'

    def lookups(self, request, model_admin):
        return [
            ('yes', 'دارد'),
            ('no', 'ندارد'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(reservations__user__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(reservations__user__isnull=True)
        return queryset


@admin.register(ConsultationTopic)
class ConsultationTopicAdmin(admin.ModelAdmin):
    """Admin panel for consultation topics"""

    list_display = [
        'name',
        'active_badge',
        'order',
        'reservations_count',
        'get_created_at_jalali'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    list_editable = ['order']

    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('name', 'slug', 'description')
        }),
        ('تنظیمات', {
            'fields': ('is_active', 'order')
        }),
    )
    actions = ['export_topics_csv']

    @admin.action(description='📥 خروجی CSV')
    def export_topics_csv(modeladmin, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename=consultation_topics.csv'

        # Prevent Excel from messing with newline
        writer = csv.writer(response, delimiter=',', quoting=csv.QUOTE_MINIMAL)

        # Header row
        writer.writerow(['عنوان', 'تعداد رزرو', 'تاریخ ایجاد'])

        for obj in queryset:
            writer.writerow([
                safe_csv(obj.name),
                safe_csv(str(obj.reservations.count())),
                safe_csv(datetime2jalali(obj.created_at)),
            ])

        return response

    def active_badge(self, obj):
        """Display active status badge"""
        if obj.is_active:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px;">✓ فعال</span>'
            )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-size: 11px;">✗ غیرفعال</span>'
        )

    active_badge.short_description = 'وضعیت'

    def get_created_at_jalali(self, obj):
        return datetime2jalali(obj.created_at)

    get_created_at_jalali.short_description = 'تاریخ ایجاد'

    def reservations_count(self, obj):
        """Count total reservations for this topic"""
        count = obj.reservations.count()
        return format_html('<strong>{}</strong>', count)

    reservations_count.short_description = 'تعداد رزرو'


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    """Admin panel for consultation service types"""

    list_display = [
        'name',
        'price_display',
        'duration_display',
        'service_type_badge',
        'active_badge',
        'order',
        'reservations_count',
        'get_created_at_jalali'
    ]
    list_filter = ['is_active', 'is_online', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    list_editable = ['order']

    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('name', 'slug', 'description')
        }),
        ('قیمت و مدت زمان', {
            'fields': ('price', 'duration')
        }),
        ('تنظیمات', {
            'fields': ('is_online', 'is_active', 'order')
        }),
    )
    actions = ['export_services_csv']

    @admin.action(description='📥 خروجی CSV')
    def export_services_csv(modeladmin, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename=service_types.csv'

        writer = csv.writer(response, delimiter=',', quoting=csv.QUOTE_MINIMAL)

        # Header
        writer.writerow(['نام سرویس', 'قیمت', 'مدت زمان', 'نوع مشاوره', 'تعداد رزرو', 'تاریخ ایجاد'])

        for obj in queryset:
            service_type_label = 'غیرحضوری' if obj.is_online else 'حضوری'

            writer.writerow([
                safe_csv(obj.name),
                safe_csv("{:,}".format(obj.price) + ' تومان'),
                safe_csv(f"{obj.duration} دقیقه"),
                safe_csv(service_type_label),
                safe_csv(obj.reservations.count()),
                safe_csv(datetime2jalali(obj.created_at)),
            ])

        return response

    def price_display(self, obj):
        """Display price with thousand separators"""
        price_str = "{:,}".format(obj.price)
        return format_html(
            '<strong style="color: #28a745;">{} تومان</strong>',
            price_str
        )

    price_display.short_description = 'قیمت'

    def duration_display(self, obj):
        """Display duration in a friendly format"""
        return f"{obj.duration} دقیقه"

    duration_display.short_description = 'مدت زمان'

    def service_type_badge(self, obj):
        """Display service type badge (online/in-person)"""
        if obj.is_online:
            return format_html(
                '<span style="background: #17a2b8; color: white; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px;">📱 غیرحضوری</span>'
            )
        return format_html(
            '<span style="background: #6f42c1; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-size: 11px;">🏢 حضوری</span>'
        )

    service_type_badge.short_description = 'نوع مشاوره'

    def active_badge(self, obj):
        """Display active status badge"""
        if obj.is_active:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px;">✓ فعال</span>'
            )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-size: 11px;">✗ غیرفعال</span>'
        )

    active_badge.short_description = 'وضعیت'

    def get_created_at_jalali(self, obj):
        return datetime2jalali(obj.created_at)

    get_created_at_jalali.short_description = 'تاریخ ایجاد'

    def reservations_count(self, obj):
        """Count total reservations for this service"""
        count = obj.reservations.count()
        return format_html('<strong>{}</strong>', count)

    reservations_count.short_description = 'تعداد رزرو'


class SlotRuleAdminForm(forms.ModelForm):
    WEEKDAYS_CHOICES = [
        ('0', 'شنبه'),
        ('1', 'یکشنبه'),
        ('2', 'دوشنبه'),
        ('3', 'سه‌شنبه'),
        ('4', 'چهارشنبه'),
        ('5', 'پنج‌شنبه'),
        ('6', 'جمعه'),
    ]

    apply_from_date = JalaliDateField(
        widget=AdminJalaliDateWidget,
        label="تاریخ شروع",
        required=False
    )
    apply_to_date = JalaliDateField(
        widget=AdminJalaliDateWidget,
        label="تاریخ پایان",
        required=False
    )

    weekdays = forms.MultipleChoiceField(
        choices=WEEKDAYS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="روزهای هفته",
        required=False
    )

    class Meta:
        model = SlotRule
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.weekdays:
            self.initial['weekdays'] = self.instance.weekdays.split(',')

    def clean_weekdays(self):
        data = self.cleaned_data.get('weekdays', [])
        return ','.join(data)


@admin.register(SlotRule)
class SlotRuleAdmin(admin.ModelAdmin):
    """Admin panel for slot generation rules"""

    list_display = [
        'name',
        'service_type',
        'time_range',
        'duration_display',
        'weekdays_display',
        'date_range',
        'get_date_range_jalali',
        'active_badge'
    ]
    list_filter = ['is_active', 'service_type', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    form = SlotRuleAdminForm
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('name', 'service_type', 'is_active')
        }),
        ('زمان‌بندی', {
            'fields': ('weekdays', 'start_time', 'end_time', 'slot_duration')
        }),
        ('محدوده تاریخی (اختیاری)', {
            'fields': ('apply_from_date', 'apply_to_date'),
            'classes': ('collapse',)
        }),
        ('اطلاعات سیستمی', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['export_slot_rule_csv']

    class Media:
        css = {
            'all': ('admin/css/django_jalali.min.css',)
        }
        js = (
            'admin/js/django_jalali.min.js',
            # 'admin/js/main_jalali.js'
        )

    @admin.action(description='خروجی CSV')
    def export_slot_rule_csv(modeladmin, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=slot_rules.csv'
        writer = csv.writer(response)

        # header
        writer.writerow(['نام', 'نوع سرویس', 'روزهای هفته', 'بازه زمانی', 'مدت هر نوبت'])

        for obj in queryset:
            writer.writerow([
                obj.name,
                obj.service_type,
                modeladmin.weekdays_csv(obj),
                f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}",
                f"{obj.slot_duration} دقیقه"
            ])

        return response

    def weekdays_csv(self, obj):
        days_map = {
            '0': 'شنبه', '1': 'یکشنبه', '2': 'دوشنبه',
            '3': 'سه‌شنبه', '4': 'چهارشنبه', '5': 'پنج‌شنبه', '6': 'جمعه'
        }
        if obj.weekdays:
            selected = [days_map.get(d.strip(), d) for d in obj.weekdays.split(',')]
            return ', '.join(selected)
        return ''

    weekdays_csv.short_description = 'روزهای هفته'

    def get_date_range_jalali(self, obj):
        start = date2jalali(obj.apply_from_date) if obj.apply_from_date else "نامحدود"
        end = date2jalali(obj.apply_to_date) if obj.apply_to_date else "نامحدود"
        return f"{start} تا {end}"

    get_date_range_jalali.short_description = 'محدوده تاریخی'

    def time_range(self, obj):
        """Display time range"""
        return format_html(
            '<strong>{}</strong> تا <strong>{}</strong>',
            obj.start_time.strftime('%H:%M'),
            obj.end_time.strftime('%H:%M')
        )

    time_range.short_description = 'بازه زمانی'

    def duration_display(self, obj):
        """Display slot duration"""
        return f"{obj.slot_duration} دقیقه"

    duration_display.short_description = 'مدت هر نوبت'

    def weekdays_display(self, obj):
        """Display selected weekdays in Persian"""
        days_map = {
            '0': 'شنبه', '1': 'یکشنبه', '2': 'دوشنبه',
            '3': 'سه‌شنبه', '4': 'چهارشنبه', '5': 'پنج‌شنبه', '6': 'جمعه'
        }
        selected = [days_map.get(d.strip(), d) for d in obj.weekdays.split(',')]
        return format_html('<span style="color: #007bff;">{}</span>', ' - '.join(selected))

    weekdays_display.short_description = 'روزهای هفته'

    def date_range(self, obj):
        """Display date range if set"""
        if obj.apply_from_date and obj.apply_to_date:
            return f"{obj.apply_from_date} تا {obj.apply_to_date}"
        elif obj.apply_from_date:
            return f"از {obj.apply_from_date}"
        elif obj.apply_to_date:
            return f"تا {obj.apply_to_date}"
        return format_html('<span style="color: #6c757d;">نامحدود</span>')

    date_range.short_description = 'محدوده تاریخی'

    def active_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html('<span style="color: green; font-size: 18px;">✓</span>')
        return format_html('<span style="color: gray; font-size: 18px;">✗</span>')

    active_badge.short_description = 'فعال'


class TimeSlotAdminForm(forms.ModelForm):
    date = JalaliDateField(widget=AdminJalaliDateWidget, label="تاریخ")
    created_at = SplitJalaliDateTimeField(widget=AdminSplitJalaliDateTime, required=False)

    class Meta:
        model = TimeSlot
        fields = "__all__"


@admin.register(TimeSlot)
class TimeSlotAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    """Admin panel for individual time slots"""

    list_display = [
        'service_type',
        'time_range',
        'get_weekday_fa',
        'get_jalali_date',
        'availability_badge',
        'expired_badge',
        'source_badge',
        'get_payment_status',
        'get_tracking_code',
        'get_reserver_name',
        'get_reserver_phone',
    ]
    list_filter = [
        JalaliDateRangeFilter,
        'is_available',
        'is_expired',
        'service_type',
        TimeSlotJalaliDateFilter,
        HasReservationFilter,
        'start_time',
        # 'end_time',
        'is_manual',
        'created_at',
    ]
    ordering = ['date', 'start_time']
    search_fields = [
        'date',
        'service_type__name',
        'reservations__full_name',
        'reservations__phone_number',
        'reservations__tracking_code',
    ]
    date_hierarchy = 'date'
    readonly_fields = ['created_by', 'created_at', 'created_from_rule', 'reservation_details', 'is_expired']
    actions = [
        'mark_as_unavailable',
        'mark_as_available',
        'mark_as_available_force',
        'delete_selected_slots',
        'mark_expired_slots',
        'mark_expired_slots_manual',
        'mark_active_slots_manual',
        'export_slots_csv',
    ]
    change_list_template = 'admin/council/timeslot_changelist.html'
    form = TimeSlotAdminForm

    class Media:
        css = {
            'all': ('admin/css/django_jalali.min.css',)
        }
        js = (
            'admin/js/django_jalali.min.js',
            # 'admin/js/main_jalali.js'
        )

    @admin.action(description='📥 خروجی به فرمت CSV')
    def export_slots_csv(self, request, queryset):
        """Export time slots to CSV with complete reservation and payment details"""
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename=time_slots.csv'

        writer = csv.writer(response, delimiter=',', quoting=csv.QUOTE_MINIMAL)

        # CSV Header
        writer.writerow([
            'نوع مشاوره',
            'زمان',
            'تاریخ',
            'روز هفته',
            'وضعیت رزرو',
            'وضعیت پرداخت',
            'مبلغ نهایی پرداخت',
            'کد پیگیری',
            'رزرو کننده',
            'شماره تماس رزرو کننده',
            'زمان رزرو',
            'زمان ایجاد نوبت'
        ])

        # Persian weekday mapping
        WEEKDAY_PERSIAN = {
            0: "دوشنبه",  # Monday
            1: "سه‌شنبه",  # Tuesday
            2: "چهارشنبه",  # Wednesday
            3: "پنج‌شنبه",  # Thursday
            4: "جمعه",  # Friday
            5: "شنبه",  # Saturday
            6: "یکشنبه",  # Sunday
        }

        def convert_to_jalali_date(date_obj):
            """Convert Gregorian date to Jalali format (YYYY/MM/DD)"""
            if not date_obj:
                return '-'
            jalali_date = jdatetime.date.fromgregorian(date=date_obj)
            return jalali_date.strftime('%Y/%m/%d')

        def convert_to_jalali_datetime(datetime_obj):
            """Convert Gregorian datetime to Jalali format (YYYY/MM/DD HH:MM:SS)"""
            if not datetime_obj:
                return '-'
            jalali_datetime = jdatetime.datetime.fromgregorian(datetime=datetime_obj)
            return jalali_datetime.strftime('%Y/%m/%d %H:%M:%S')

        def format_time_range(start_time, end_time):
            """Format time range as HH:MM - HH:MM"""
            return f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

        # Process each slot in queryset
        for slot in queryset:
            reservation = slot.reservations.first()

            # Get weekday in Persian
            weekday_persian = WEEKDAY_PERSIAN.get(slot.date.weekday(), "-")

            # Availability status
            availability_status = "رزرو شده" if not slot.is_available else "در دسترس"

            # Extract reservation and payment details
            if reservation:
                # Get successful payment
                successful_payment = reservation.payments.filter(status='success').first()

                payment_status = (
                    reservation.get_payment_status_display()
                    if hasattr(reservation, 'get_payment_status_display')
                    else reservation.payment_status
                )
                final_amount = successful_payment.amount if successful_payment else "-"
                tracking_code = reservation.tracking_code or "-"
                reserver_name = reservation.full_name or "-"
                reserver_phone = reservation.phone_number or "-"
                booking_time = convert_to_jalali_datetime(reservation.reserved_at)
            else:
                payment_status = "-"
                final_amount = "-"
                tracking_code = "-"
                reserver_name = "-"
                reserver_phone = "-"
                booking_time = "-"

            # Write row to CSV
            writer.writerow([
                safe_csv(slot.service_type.name),
                safe_csv(format_time_range(slot.start_time, slot.end_time)),
                safe_csv(convert_to_jalali_date(slot.date)),
                safe_csv(weekday_persian),
                safe_csv(availability_status),
                safe_csv(payment_status),
                safe_csv(final_amount),
                safe_csv(tracking_code),
                safe_csv(reserver_name),
                safe_csv(reserver_phone),
                safe_csv(booking_time),
                safe_csv(convert_to_jalali_datetime(slot.created_at)),
            ])

        return response

    def get_actions(self, request):
        actions = super().get_actions(request)

        if 'delete_selected' in actions:
            function, name, _ = actions['delete_selected']

            actions['delete_selected'] = (function, name, '🗑️ حذف بازه های زمانی (بدون رزرو)')

        return actions

    def changelist_view(self, request, extra_context=None):
        """
        Override changelist to auto-mark expired slots when admin visits the page
        """

        expired_count = mark_expired_time_slots()

        if expired_count > 0:
            self.message_user(
                request,
                f'🔄 {expired_count} نوبت منقضی شده خودکار به‌روزرسانی شد',
                messages.SUCCESS
            )

        return super().changelist_view(request, extra_context)

    @admin.display(description="اطلاعات رزرو")
    def reservation_details(self, obj):
        reservation = obj.reservations.first()
        if not reservation:
            return format_html(
                "<span style='color:#888;'>هیچ رزروی برای این بازه ثبت نشده است.</span>"
            )

        excluded_fields = {
            'id', 'created_at', 'updated_at', 'deleted_at',
            'user', 'time_slot'
        }

        status_display = {
            'pending': ('در انتظار تایید شماره', '#fd7e14'),
            'phone_verified': ('شماره تایید شده - در انتظار پرداخت', '#17a2b8'),
            'paid': ('پرداخت شده', '#007bff'),
            'completed': ('انجام شده', '#28a745'),
            'cancelled': ('لغو شده', '#dc3545'),
        }

        payment_display = {
            'paid': ('پرداخت شده', '#28a745'),
            'unpaid': ('پرداخت نشده', '#fd7e14'),
            'refunded': ('بازگشت داده شده', '#6c757d'),
        }

        rows = []

        for field in reservation._meta.fields:
            if field.name in excluded_fields:
                continue

            label = field.verbose_name
            value = getattr(reservation, field.name)

            if isinstance(value, (datetime, date)):
                try:
                    j_date = jdatetime.datetime.fromgregorian(
                        datetime=value
                    ).strftime("%Y/%m/%d %H:%M:%S")
                    value = j_date
                except:
                    pass

            # وضعیت رزرو
            if field.name == 'status':
                fa, color = status_display.get(value, (value, "#6c757d"))
                value = mark_safe(
                    f"<span style='background:{color}; color:white; padding:3px 8px; border-radius:6px;'>{fa}</span>"
                )

            # وضعیت پرداخت
            if field.name == 'payment_status':
                fa, color = payment_display.get(value, (value, "#6c757d"))
                value = mark_safe(
                    f"<span style='background:{color}; color:white; padding:3px 8px; border-radius:6px;'>{fa}</span>"
                )

            # مقدارهای خالی
            if value in ['', None]:
                value = mark_safe("<span style='color:#999;'>—</span>")

            rows.append((label, value))

        return format_html(
            """
            <div style="
                border:1px solid #ddd;
                border-radius:10px;
                padding:15px;
                background:#fafafa;
                line-height:2;
            ">
                <h3 style="margin-top:0; font-size:16px; font-weight:bold;">جزئیات رزرو</h3>
                <table style="width:100%; border-collapse:collapse;">
                    {}
                </table>
            </div>
            """,
            format_html_join(
                "",
                """
                <tr>
                    <td style="padding:6px; width:200px; font-weight:bold; color:#333;">{}</td>
                    <td style="padding:6px;">{}</td>
                </tr>
                """,
                rows
            )
        )

    fieldsets = (
        ('اطلاعات بازه زمانی', {
            'fields': ('service_type', 'date', 'start_time', 'end_time')
        }),
        ('وضعیت', {
            'fields': ('is_available', 'is_expired')
        }),
        ('اطلاعات سیستمی', {
            'fields': ('is_manual', 'created_from_rule', 'created_by', 'created_at'),
            'classes': ('collapse',)
        }),
        ('اطلاعات رزرو', {
            'fields': ('reservation_details',),
        }),
    )

    def get_jalali_date(self, obj):
        return date2jalali(obj.date)

    get_jalali_date.short_description = 'تاریخ'
    get_jalali_date.admin_order_field = 'date'

    def get_weekday_fa(self, obj):
        """Return weekday in Persian for the given date"""
        weekday_map = {
            0: "شنبه",
            1: "یکشنبه",
            2: "دوشنبه",
            3: "سه‌شنبه",
            4: "چهارشنبه",
            5: "پنجشنبه",
            6: "جمعه",
        }

        # weekday() بر اساس Monday=0 تا Sunday=6
        week_day_index = obj.date.weekday()
        return weekday_map.get(week_day_index, "-")

    get_weekday_fa.short_description = 'روز هفته'
    get_weekday_fa.admin_order_field = 'date'

    def get_urls(self):
        """Add custom URLs for bulk generation"""
        urls = super().get_urls()
        custom_urls = [
            path(
                'bulk-generate/',
                self.admin_site.admin_view(self.bulk_generate_view),
                name='timeslot_bulk_generate'
            ),
            path(
                'generate-from-rule/',
                self.admin_site.admin_view(self.generate_from_rule_view),
                name='timeslot_generate_from_rule'
            ),
        ]
        return custom_urls + urls

    def bulk_generate_view(self, request):
        """Manual bulk slot generation view"""
        if request.method == 'POST':
            try:
                # Get form data
                service_type_id = request.POST.get('service_type')
                start_date = datetime.strptime(request.POST['start_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(request.POST['end_date'], '%Y-%m-%d').date()
                start_time = datetime.strptime(request.POST['start_time'], '%H:%M').time()
                end_time = datetime.strptime(request.POST['end_time'], '%H:%M').time()
                interval = int(request.POST['interval'])
                weekdays = request.POST.getlist('weekdays')

                service_type = ServiceType.objects.get(id=service_type_id)

                # Generate slots
                created_count = 0
                current_date = start_date

                while current_date <= end_date:
                    # Check if current weekday is selected
                    if str(current_date.weekday()) in weekdays:
                        # Generate time slots for this day
                        current_time = start_time

                        while current_time < end_time:
                            # Calculate end time for this slot
                            slot_end = (
                                    datetime.combine(current_date, current_time) +
                                    timedelta(minutes=interval)
                            ).time()

                            if slot_end > end_time:
                                break

                            # Create slot if not exists
                            slot, created = TimeSlot.objects.get_or_create(
                                service_type=service_type,
                                date=current_date,
                                start_time=current_time,
                                end_time=slot_end,
                                defaults={
                                    'is_available': True,
                                    'is_manual': True,
                                    'created_by': request.user
                                }
                            )

                            if created:
                                created_count += 1

                            # Move to next slot
                            current_time = slot_end

                    current_date += timedelta(days=1)

                messages.success(
                    request,
                    f'✓ {created_count} نوبت با موفقیت ایجاد شد!'
                )
                return redirect('admin:council_timeslot_changelist')

            except Exception as e:
                messages.error(request, f'خطا: {str(e)}')

        # GET request - show form
        context = {
            'title': 'تولید گروهی نوبت‌ها (گروهی)',
            'service_types': ServiceType.objects.filter(is_active=True),
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        return render(request, 'admin/council/timeslot_bulk_generate.html', context)

    def generate_from_rule_view(self, request):
        """Generate slots from SlotRule patterns"""
        if request.method == 'POST':
            try:
                rule_id = request.POST.get('rule_id')
                start_date = datetime.strptime(request.POST['start_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(request.POST['end_date'], '%Y-%m-%d').date()

                rule = SlotRule.objects.get(id=rule_id, is_active=True)

                # Validate date range against rule's apply dates
                effective_start_date = start_date
                effective_end_date = end_date

                # Check if requested range is completely outside rule's range
                if rule.apply_from_date and end_date < rule.apply_from_date:
                    messages.error(
                        request,
                        f'❌ خطا: بازه زمانی درخواستی ({start_date} تا {end_date}) '
                        f'قبل از تاریخ شروع الگو ({rule.apply_from_date}) است.'
                    )
                    return redirect('admin:timeslot_generate_from_rule')

                if rule.apply_to_date and start_date > rule.apply_to_date:
                    messages.error(
                        request,
                        f'❌ خطا: بازه زمانی درخواستی ({start_date} تا {end_date}) '
                        f'بعد از تاریخ پایان الگو ({rule.apply_to_date}) است.'
                    )
                    return redirect('admin:timeslot_generate_from_rule')

                # Adjust dates to fit within rule's range
                if rule.apply_from_date and start_date < rule.apply_from_date:
                    effective_start_date = rule.apply_from_date
                    messages.warning(
                        request,
                        f'⚠️ توجه: تاریخ شروع از {start_date} به {effective_start_date} '
                        f'تغییر یافت (مطابق با تاریخ شروع الگو)'
                    )

                if rule.apply_to_date and end_date > rule.apply_to_date:
                    effective_end_date = rule.apply_to_date
                    messages.warning(
                        request,
                        f'⚠️ توجه: تاریخ پایان از {end_date} به {effective_end_date} '
                        f'تغییر یافت (مطابق با تاریخ پایان الگو)'
                    )

                weekdays = rule.get_weekdays_list()
                created_count = 0
                current_date = effective_start_date

                while current_date <= effective_end_date:
                    # Check if current weekday matches rule
                    if current_date.weekday() in weekdays:
                        # Generate slots for this day
                        current_time = rule.start_time

                        while current_time < rule.end_time:
                            slot_end = (
                                    datetime.combine(current_date, current_time) +
                                    timedelta(minutes=rule.slot_duration)
                            ).time()

                            if slot_end > rule.end_time:
                                break

                            slot, created = TimeSlot.objects.get_or_create(
                                service_type=rule.service_type,
                                date=current_date,
                                start_time=current_time,
                                end_time=slot_end,
                                defaults={
                                    'is_available': True,
                                    'is_manual': False,
                                    'created_from_rule': rule,
                                    'created_by': request.user
                                }
                            )

                            if created:
                                created_count += 1

                            current_time = slot_end

                    current_date += timedelta(days=1)

                if created_count > 0:
                    messages.success(
                        request,
                        f'✓ {created_count} نوبت از الگو "{rule.name}" '
                        f'برای بازه {effective_start_date} تا {effective_end_date} ایجاد شد!'
                    )
                else:
                    messages.warning(
                        request,
                        f'⚠️ هیچ نوبتی ایجاد نشد. لطفاً بازه زمانی و تنظیمات الگو را بررسی کنید.'
                    )
                return redirect('admin:council_timeslot_changelist')

            except Exception as e:
                messages.error(request, f'❌ خطا: {str(e)}')

        # GET request
        context = {
            'title': 'تولید نوبت از الگو',
            'rules': SlotRule.objects.filter(is_active=True).select_related('service_type'),
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        return render(request, 'admin/council/timeslot_from_rule.html', context)

    def time_range(self, obj):
        """Display time range"""
        return format_html(
            '{} - {}',
            obj.start_time.strftime('%H:%M'),
            obj.end_time.strftime('%H:%M')
        )

    time_range.short_description = 'زمان'

    def availability_badge(self, obj):
        """Display availability status"""
        if obj.is_available:
            return format_html(
                '<span style="background: #BADFDB; color: dark; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px;">در دسترس</span>'
            )
        return format_html(
            '<span style="background: #EDA35A; color: dark; padding: 3px 10px; '
            'border-radius: 12px; font-size: 11px;">رزرو شده</span>'
        )

    availability_badge.short_description = 'وضعیت'

    def expired_badge(self, obj):
        """Display expiration status"""
        if obj.is_expired:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px;">منقضی شده</span>'
            )
        return format_html(
            '<span style="background: #28a745; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-size: 11px;">✓ فعال</span>'
        )

    expired_badge.short_description = 'انقضا'

    def source_badge(self, obj):
        """Display how slot was created"""
        if obj.is_manual:
            return format_html(
                '<span style="background: #7F55B1; color: white; padding: 2px 8px; '
                'border-radius: 8px; font-size: 10px;">گروهی</span>'
            )
        elif obj.created_from_rule:
            return format_html(
                '<span style="background: #AEC8A4; color: white; padding: 2px 8px; '
                'border-radius: 8px; font-size: 10px;" title="{}">از الگو</span>',
                obj.created_from_rule.name
            )
        return format_html('<span style="background: #B7B7B7; color: white; padding: 2px 8px; '
                           'border-radius: 8px; font-size: 10px;">دستی</span>',
                           )

    source_badge.short_description = 'منبع'

    def mark_as_unavailable(self, request, queryset):
        """Mark selected slots as unavailable"""
        updated = queryset.update(is_available=False)
        messages.success(request, f'{updated} نوبت به عنوان غیرقابل دسترس علامت‌گذاری شد.')

    mark_as_unavailable.short_description = '👎 علامت‌گذاری به عنوان غیرقابل دسترس (رزرو شده)'

    def mark_as_available(self, request, queryset):
        """Mark selected slots as available"""
        # Only mark slots without reservations as available
        slots_with_reservations = queryset.filter(reservations__isnull=False).count()
        updated = queryset.filter(reservations__isnull=True).update(is_available=True)

        messages.success(request, f'{updated} نوبت به عنوان قابل دسترس علامت‌گذاری شد.')
        if slots_with_reservations > 0:
            messages.warning(
                request,
                f'{slots_with_reservations} نوبت دارای رزرو بودند و تغییر نکردند.'
            )

    mark_as_available.short_description = '👍 علامت‌گذاری به عنوان قابل دسترس'

    def mark_as_available_force(self, request, queryset):
        """
        Force mark selected slots as available (even if they have reservations)
        WARNING: This will not cancel the reservations, just marks slots as available
        """
        slots_with_reservations = queryset.filter(reservations__isnull=False).distinct()
        slots_count = slots_with_reservations.count()

        if slots_count > 0:
            # Show confirmation warning
            reservation_details = []
            for slot in slots_with_reservations[:5]:  # Show first 5
                reservations = slot.reservations.all()[:3]  # Show first 3 reservations
                for res in reservations:
                    reservation_details.append(
                        f"• {res.tracking_code} - {res.full_name} ({slot.date} {slot.start_time})"
                    )

            warning_msg = (
                    f'⚠️ هشدار: {slots_count} نوبت دارای رزرو هستند!\n\n'
                    f'نمونه رزروها:\n' + '\n'.join(reservation_details[:5])
            )

            if len(reservation_details) > 5:
                warning_msg += f'\n... و {len(reservation_details) - 5} رزرو دیگر'

            messages.warning(request, warning_msg)

        # Force update all selected slots
        updated = queryset.update(is_available=True)

        messages.success(
            request,
            f'✓ {updated} نوبت به صورت اجباری به عنوان قابل دسترس علامت‌گذاری شد.'
        )

        if slots_count > 0:
            messages.error(
                request,
                f'⚠️ توجه: {slots_count} نوبت دارای رزرو فعال بودند. '
                'رزروها لغو نشده‌اند و ممکن است تداخل ایجاد شود!'
            )

    mark_as_available_force.short_description = '🔓 علامت‌گذاری اجباری به عنوان قابل دسترس (Force)'

    def mark_expired_slots(self, request, queryset):
        """Manually mark slots as expired if less than 24h remains"""

        tehran_tz = pytz.timezone('Asia/Tehran')
        now = timezone.now().astimezone(tehran_tz)
        expired_count = 0

        for slot in queryset:
            slot_datetime = tehran_tz.localize(
                datetime.combine(slot.date, slot.start_time)
            )

            # 24 Hours deadline
            expiration_deadline = slot_datetime - timedelta(days=1)

            if now >= expiration_deadline:
                if not slot.is_expired or slot.is_available:
                    slot.is_expired = True
                    slot.is_available = False
                    slot.save(update_fields=['is_expired', 'is_available'])
                    expired_count += 1

        messages.success(request, f'✓ {expired_count} نوبت (که کمتر از ۲۴ ساعت به شروع آن‌ها مانده) منقضی شد.')

    mark_expired_slots.short_description = '⏰ علامت‌گذاری نوبت‌های گذشته به عنوان منقضی'

    def mark_expired_slots_manual(self, request, queryset):
        """
        Force mark slots as expired (Manual)
        """
        updated_count = queryset.update(is_expired=True, is_available=False)

        messages.success(
            request,
            f'✓ {updated_count} نوبت به صورت دستی «منقضی» و از دسترس خارج شد.'
        )

    mark_expired_slots_manual.short_description = '⛔ منقضی کردن دستی نوبت‌ها (بدون شرط زمان)'

    def mark_active_slots_manual(self, request, queryset):
        """
        Force mark slots as active/available (Un-expire)
        """
        updated_count = queryset.update(is_expired=False)

        messages.success(
            request,
            f'✓ {updated_count} نوبت رفع انقضا شد (وضعیت رزرو و در دسترس بودن تغییر نکرد).'
        )

    mark_active_slots_manual.short_description = '✅ فعال‌سازی مجدد و لغو انقضا'

    def delete_selected_slots(self, request, queryset):
        """
        Hard Delete selected slots + Force delete related reservations
        """
        related_reservations = Reservation.objects.filter(time_slot__in=queryset)
        res_count = related_reservations.count()
        slots_count = queryset.count()

        if res_count > 0:
            related_reservations.delete()

        queryset.delete()

        if res_count > 0:
            messages.warning(
                request,
                f'💥 عملیات سنگین: {slots_count} نوبت به همراه {res_count} رزرو متصل به آن‌ها، '
                f'به صورت کامل و فیزیکی از دیتابیس حذف شدند.'
            )
        else:
            messages.success(
                request,
                f'🗑️ {slots_count} نوبت با موفقیت حذف فیزیکی شدند.'
            )

    delete_selected_slots.short_description = '💀 حذف فیزیکی و اجباری (همراه با رزروها)'

    def get_tracking_code(self, obj):
        reservation = obj.reservations.first()
        if reservation and reservation.tracking_code:
            return format_html(
                '<code style="font-size: 14px; color: #d63384; user-select: all;">{}</code>',
                reservation.tracking_code
            )
        return "-"

    get_tracking_code.short_description = 'کد پیگیری'
    get_tracking_code.admin_order_field = 'reservations__tracking_code'

    def get_reserver_name(self, obj):
        reservation = obj.reservations.first()
        return reservation.full_name if reservation else "-"

    get_reserver_name.short_description = "رزرو کننده"
    get_reserver_name.admin_order_field = "reservations__full_name"

    def get_reserver_phone(self, obj):
        reservation = obj.reservations.first()
        return reservation.phone_number if reservation else "-"

    get_reserver_phone.short_description = "شماره تماس"
    get_reserver_phone.admin_order_field = "reservations__phone_number"

    def get_payment_status(self, obj):
        reservation = obj.reservations.first()
        if not reservation:
            return format_html('<span style="color: gray;">رزرو نشده</span>')

        colors = {
            'unpaid': '#E55050',
            'paid': '#59AC77',
            'refunded': '#6c757d',
        }
        color = colors.get(reservation.payment_status, "#6c757d")

        return format_html(
            '<span style="background:{}; color:whitesmoke; padding:3px 8px; border-radius:8px; font-size:11px;">{}</span>',
            color,
            reservation.get_payment_status_display()
        )

    get_payment_status.short_description = "پرداخت"


@admin.register(Reservation)
class ReservationAdmin(ModelAdminJalaliMixin, admin.ModelAdmin):
    """Admin panel for reservations"""

    list_display = [
        'row_number',
        'tracking_code_copy',
        'full_name_display',
        'phone_number',
        'service_type',
        'consultation_topic_display',
        'slot_info',
        'status_badge',
        'payment_badge',
        'get_jalali_reserve_date',
    ]
    list_filter = [
        'status',
        'payment_status',
        'service_type',
        'consultation_topic',
        JalaliDateFilter,
        'phone_verified_at',
        ('time_slot__date', admin.DateFieldListFilter),
        'created_at',
    ]
    search_fields = [
        'tracking_code',
        'phone_number',
        'full_name',
        'email',
        'user__phone',
        'user__full_name'
    ]
    readonly_fields = [
        'tracking_code',
        'phone_verified_at',
        'reserved_at',
        'created_at',
        'updated_at'
    ]
    list_display_links = ['row_number', 'full_name_display']
    date_hierarchy = 'time_slot__date'
    actions = [
        'mark_as_completed',
        'mark_as_cancelled',
        'export_selected_csv',
        'export_selected_pdf_admin',
        'export_selected_pdf_user',
    ]

    fieldsets = (
        ('اطلاعات رزرو', {
            'fields': ('tracking_code', 'service_type', 'time_slot', 'consultation_topic')
        }),
        ('اطلاعات تماس', {
            'fields': (
                'full_name',
                'phone_number',
                'email'
            )
        }),
        ('وضعیت', {
            'fields': ('status', 'payment_status', 'phone_verified_at')
        }),
        ('کاربر (پس از تایید OTP)', {
            'fields': ('user',),
            'classes': ('collapse',)
        }),
        ('جزئیات بیشتر', {
            'fields': ('message', 'prescription'),
            'classes': ('collapse',)
        }),
        ('اطلاعات سیستمی', {
            'fields': ('reserved_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def row_number(self, obj):
        return f"#{obj.id}"

    row_number.short_description = 'شناسه'

    def tracking_code_copy(self, obj):
        return format_html(
            '<code style="font-size: 14px; color: #d63384; user-select: all;">{}</code>',
            obj.tracking_code
        )

    tracking_code_copy.short_description = 'کد پیگیری'

    def consultation_topic_display(self, obj):
        """Display consultation topic"""
        if obj.consultation_topic:
            return format_html(
                '<span style="background: #17a2b8; color: white; padding: 3px 8px; '
                'border-radius: 8px; font-size: 11px;">{}</span>',
                obj.consultation_topic.name
            )
        return format_html('<span style="color: #999;">—</span>')

    consultation_topic_display.short_description = 'عنوان مشاوره'

    def get_jalali_reserve_date(self, obj):
        weekday_map = {
            "Saturday": "شنبه",
            "Sunday": "یکشنبه",
            "Monday": "دوشنبه",
            "Tuesday": "سه‌شنبه",
            "Wednesday": "چهارشنبه",
            "Thursday": "پنجشنبه",
            "Friday": "جمعه",
        }

        if obj.time_slot:
            week_day_en = obj.time_slot.date.strftime('%A')
            week_day_fa = weekday_map.get(week_day_en, week_day_en)

            g_date = obj.time_slot.date.strftime('%Y-%m-%d')

            return format_html(
                '<strong style="font-size:13px;">{}</strong><br>'
                '<small style="color:#6c757d;">{}</small>',
                week_day_fa,
                g_date
            )

        return "-"

    get_jalali_reserve_date.short_description = 'تاریخ نوبت'
    get_jalali_reserve_date.admin_order_field = 'time_slot__date'

    def save_model(self, request, obj, form, change):
        """Auto-mark time slot as unavailable when reservation is created/updated"""
        old_time_slot = None
        if change and obj.pk:
            try:
                old_reservation = Reservation.objects.get(pk=obj.pk)
                old_time_slot = old_reservation.time_slot
            except Reservation.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)

        if obj.time_slot:
            obj.time_slot.is_available = False
            obj.time_slot.save(update_fields=['is_available'])

        if old_time_slot and old_time_slot != obj.time_slot:
            if not old_time_slot.reservations.exclude(pk=obj.pk).exists():
                old_time_slot.is_available = True
                old_time_slot.save(update_fields=['is_available'])

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter time slots to show only available ones and consultation topics"""
        if db_field.name == "time_slot":
            obj_id = request.resolver_match.kwargs.get('object_id')

            if obj_id:
                try:
                    current_reservation = Reservation.objects.get(pk=obj_id)
                    kwargs["queryset"] = TimeSlot.objects.filter(
                        models.Q(is_available=True) | models.Q(pk=current_reservation.time_slot.pk),
                        deleted_at__isnull=True,
                        is_expired=False
                    ).order_by('date', 'start_time')
                except Reservation.DoesNotExist:
                    kwargs["queryset"] = TimeSlot.objects.filter(
                        is_available=True,
                        deleted_at__isnull=True,
                        is_expired=False
                    ).order_by('date', 'start_time')
            else:
                kwargs["queryset"] = TimeSlot.objects.filter(
                    is_available=True,
                    deleted_at__isnull=True,
                    is_expired=False
                ).order_by('date', 'start_time')

        elif db_field.name == "consultation_topic":
            kwargs["queryset"] = ConsultationTopic.objects.filter(
                is_active=True
            ).order_by('order', 'name')

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def delete_model(self, request, obj):
        """Mark time slot as available when reservation is deleted"""
        time_slot = obj.time_slot
        super().delete_model(request, obj)

        if time_slot and not time_slot.reservations.exists():
            time_slot.is_available = True
            time_slot.save(update_fields=['is_available'])
            messages.info(request, f'بازه زمانی {time_slot} مجدداً قابل رزرو شد.')

    def delete_queryset(self, request, queryset):
        """Handle bulk deletion - mark time slots as available"""
        time_slots = set(queryset.values_list('time_slot', flat=True))
        super().delete_queryset(request, queryset)

        for slot_id in time_slots:
            try:
                slot = TimeSlot.objects.get(pk=slot_id)
                if not slot.reservations.exists():
                    slot.is_available = True
                    slot.save(update_fields=['is_available'])
            except TimeSlot.DoesNotExist:
                pass

        messages.info(request, 'بازه‌های زمانی بدون رزرو مجدداً قابل رزرو شدند.')

    def full_name_display(self, obj):
        """Display full name with link to user if exists"""
        full_name = obj.full_name
        if obj.user:
            url = f'/admin/accounts/user/{obj.user.id}/change/'
            return format_html(
                '<a href="{}" style="font-weight: bold;">{}</a>',
                url,
                full_name
            )
        return format_html('<strong>{}</strong>', full_name)

    full_name_display.short_description = 'نام و نام خانوادگی'

    def slot_info(self, obj):
        """Display Jalali date + time range (no weekday)"""
        if not obj.time_slot:
            return "-"

        j_date = date2jalali(obj.time_slot.date)

        return format_html(
            '<strong>{}</strong><br/>'
            '<small style="color: #6c757d;">{} - {}</small>',
            j_date,
            obj.time_slot.start_time.strftime('%H:%M'),
            obj.time_slot.end_time.strftime('%H:%M')
        )

    slot_info.short_description = 'زمان نوبت'

    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'pending': '#FF9130',
            'phone_verified': '#87A2FF',
            'paid': '#59AC77',
            'completed': '#8E7AB5',
            'cancelled': '#E55050',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_badge.short_description = 'وضعیت'

    def payment_badge(self, obj):
        """Display payment status"""
        colors = {
            'unpaid': '#E55050',
            'paid': '#59AC77',
            'refunded': '#44444E',
        }
        icons = {
            'unpaid': '✗',
            'paid': '✓',
            'refunded': '↩',
        }
        color = colors.get(obj.payment_status, '#6c757d')
        icon = icons.get(obj.payment_status, '?')

        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-size: 11px;">{} {}</span>',
            color,
            icon,
            obj.get_payment_status_display()
        )

    payment_badge.short_description = 'پرداخت'

    def mark_as_completed(self, request, queryset):
        """Mark selected reservations as completed"""
        updated = queryset.filter(status='paid').update(status='completed')
        messages.success(request, f'{updated} رزرو به عنوان انجام شده علامت‌گذاری شد.')

        if updated < queryset.count():
            messages.warning(
                request,
                'فقط رزروهای پرداخت شده می‌توانند به عنوان انجام شده علامت‌گذاری شوند.'
            )

    mark_as_completed.short_description = 'علامت‌گذاری به عنوان انجام شده'

    def mark_as_cancelled(self, request, queryset):
        """Cancel selected reservations"""
        updated = queryset.exclude(status__in=['completed', 'cancelled']).update(
            status='cancelled'
        )
        # Also mark time slots as available again
        for reservation in queryset.filter(status='cancelled'):
            reservation.time_slot.is_available = True
            reservation.time_slot.save()

        messages.success(request, f'{updated} رزرو لغو شد.')

    mark_as_cancelled.short_description = 'لغو رزرو'

    @admin.action(description='📥 خروجی CSV (فیلتر شده)')
    def export_selected_csv(self, request, queryset):
        """
        Export selected reservations to CSV with all fields
        """
        fields = [
            'id',
            'tracking_code',
            'full_name',
            'phone_number',
            'email',
            'service_type',
            'consultation_topic',
            'status',
            'payment_status',
            'created_at',
            'phone_verified_at',
        ]

        return export_to_csv(queryset, 'reservations', fields)

    # ========== PDF Export (Admin) ==========
    @admin.action(description='📄 خروجی PDF ادمین (همه رزروها)')
    def export_selected_pdf_admin(self, request, queryset):
        """
        Export selected reservations as admin PDF reports
        """
        if queryset.count() == 1:
            # تک رزرو - یک PDF
            reservation = queryset.first()
            return generate_admin_receipt_pdf(reservation)
        else:
            # چند رزرو - ZIP فایل
            return self._export_multiple_pdf_admin(request, queryset)

    # ========== PDF Export (User) ==========
    @admin.action(description='📄 خروجی PDF کاربر (برای ارسال)')
    def export_selected_pdf_user(self, request, queryset):
        """
        Export selected reservations as user-friendly PDF receipts
        """
        if queryset.count() == 1:
            # تک رزرو - یک PDF
            reservation = queryset.first()
            return generate_user_receipt_pdf(reservation)
        else:
            # چند رزرو - ZIP فایل
            return self._export_multiple_pdf_user(request, queryset)

    # ========== Helper: Multiple PDFs as ZIP ==========
    def _export_multiple_pdf_admin(self, request, queryset):
        """
        Export multiple reservations as ZIP of admin PDFs
        """
        import zipfile
        from io import BytesIO

        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for reservation in queryset:
                # Generate PDF
                pdf_response = generate_admin_receipt_pdf(reservation)
                pdf_content = pdf_response.content

                # Add to ZIP
                filename = f"admin_{reservation.tracking_code}.pdf"
                zip_file.writestr(filename, pdf_content)

        zip_buffer.seek(0)

        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="admin_receipts_{queryset.count()}.zip"'
        return response

    def _export_multiple_pdf_user(self, request, queryset):
        """
        Export multiple reservations as ZIP of user PDFs
        """
        import zipfile
        from io import BytesIO

        zip_buffer = BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for reservation in queryset:
                # Generate PDF
                pdf_response = generate_user_receipt_pdf(reservation)
                pdf_content = pdf_response.content

                # Add to ZIP
                filename = f"receipt_{reservation.tracking_code}.pdf"
                zip_file.writestr(filename, pdf_content)

        zip_buffer.seek(0)

        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="user_receipts_{queryset.count()}.zip"'
        return response
