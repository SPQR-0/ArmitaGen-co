from datetime import datetime, timedelta

from django.contrib import admin
from django.contrib import messages
from django.db import models
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html

from .models import ServiceType, SlotRule, TimeSlot, Reservation


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
        'reservations_count'
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

    def reservations_count(self, obj):
        """Count total reservations for this service"""
        count = obj.reservations.count()
        return format_html('<strong>{}</strong>', count)

    reservations_count.short_description = 'تعداد رزرو'


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
        'active_badge'
    ]
    list_filter = ['is_active', 'service_type', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']

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


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    """Admin panel for individual time slots"""

    list_display = [
        'date',
        'service_type',
        'time_range',
        'availability_badge',
        'source_badge',
        'created_by',
        'created_at'
    ]
    list_filter = [
        'is_available',
        'service_type',
        'date',
        'is_manual',
        'created_at'
    ]
    search_fields = ['date', 'service_type__name']
    date_hierarchy = 'date'
    readonly_fields = ['created_by', 'created_at', 'created_from_rule']
    actions = ['mark_as_unavailable', 'mark_as_available', 'mark_as_available_force', 'delete_selected_slots']
    change_list_template = 'admin/council/timeslot_changelist.html'

    fieldsets = (
        ('اطلاعات نوبت', {
            'fields': ('service_type', 'date', 'start_time', 'end_time')
        }),
        ('وضعیت', {
            'fields': ('is_available',)
        }),
        ('اطلاعات سیستمی', {
            'fields': ('is_manual', 'created_from_rule', 'created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

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
            'title': 'تولید گروهی نوبت‌ها (دستی)',
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
                '<span style="background: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 12px; font-size: 11px;">✓ در دسترس</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 3px 10px; '
            'border-radius: 12px; font-size: 11px;">✗ رزرو شده</span>'
        )

    availability_badge.short_description = 'وضعیت'

    def source_badge(self, obj):
        """Display how slot was created"""
        if obj.is_manual:
            return format_html(
                '<span style="background: #6f42c1; color: white; padding: 2px 8px; '
                'border-radius: 8px; font-size: 10px;">دستی</span>'
            )
        elif obj.created_from_rule:
            return format_html(
                '<span style="background: #17a2b8; color: white; padding: 2px 8px; '
                'border-radius: 8px; font-size: 10px;" title="{}">از الگو</span>',
                obj.created_from_rule.name
            )
        return format_html('<span style="color: #6c757d;">-</span>')

    source_badge.short_description = 'منبع'

    def mark_as_unavailable(self, request, queryset):
        """Mark selected slots as unavailable"""
        updated = queryset.update(is_available=False)
        messages.success(request, f'{updated} نوبت به عنوان غیرقابل دسترس علامت‌گذاری شد.')

    mark_as_unavailable.short_description = 'علامت‌گذاری به عنوان غیرقابل دسترس'

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

    mark_as_available.short_description = 'علامت‌گذاری به عنوان قابل دسترس'

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

    def delete_selected_slots(self, request, queryset):
        """Soft delete selected slots"""
        # Only delete slots without reservations
        slots_with_reservations = queryset.filter(reservations__isnull=False)
        can_delete = queryset.filter(reservations__isnull=True)

        deleted_count = can_delete.count()
        can_delete.update(deleted_at=datetime.now())

        messages.success(request, f'{deleted_count} نوبت حذف شد.')
        if slots_with_reservations.exists():
            messages.warning(
                request,
                f'{slots_with_reservations.count()} نوبت دارای رزرو بودند و حذف نشدند.'
            )

    delete_selected_slots.short_description = 'حذف نوبت‌های انتخاب شده'


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """Admin panel for reservations"""

    list_display = [
        'tracking_code',
        'full_name_display',
        'phone_number',
        'service_type',
        'slot_info',
        'status_badge',
        'payment_badge',
        'created_at'
    ]
    list_filter = [
        'status',
        'payment_status',
        'service_type',
        'created_at',
        'phone_verified_at'
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
    date_hierarchy = 'created_at'
    actions = ['mark_as_completed', 'mark_as_cancelled', 'export_to_pdf']

    fieldsets = (
        ('اطلاعات رزرو', {
            'fields': ('tracking_code', 'service_type', 'time_slot')
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
        """Filter time slots to show only available ones"""
        if db_field.name == "time_slot":
            obj_id = request.resolver_match.kwargs.get('object_id')

            if obj_id:
                try:
                    current_reservation = Reservation.objects.get(pk=obj_id)
                    kwargs["queryset"] = TimeSlot.objects.filter(
                        models.Q(is_available=True) | models.Q(pk=current_reservation.time_slot.pk),
                        deleted_at__isnull=True
                    ).order_by('date', 'start_time')
                except Reservation.DoesNotExist:
                    kwargs["queryset"] = TimeSlot.objects.filter(
                        is_available=True,
                        deleted_at__isnull=True
                    ).order_by('date', 'start_time')
            else:
                kwargs["queryset"] = TimeSlot.objects.filter(
                    is_available=True,
                    deleted_at__isnull=True
                ).order_by('date', 'start_time')

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
        """Display slot date and time"""
        return format_html(
            '<strong>{}</strong><br/><small style="color: #6c757d;">{} - {}</small>',
            obj.time_slot.date,
            obj.time_slot.start_time.strftime('%H:%M'),
            obj.time_slot.end_time.strftime('%H:%M')
        )

    slot_info.short_description = 'زمان نوبت'

    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'pending': '#ffc107',
            'phone_verified': '#17a2b8',
            'paid': '#28a745',
            'completed': '#6f42c1',
            'cancelled': '#dc3545',
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
            'unpaid': '#dc3545',
            'paid': '#28a745',
            'refunded': '#6c757d',
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

    def export_to_pdf(self, request, queryset):
        """Export selected reservations to PDF (placeholder)"""
        messages.info(
            request,
            f'{queryset.count()} رزرو برای خروجی PDF انتخاب شد. '
            'این قابلیت به زودی اضافه خواهد شد.'
        )

    export_to_pdf.short_description = 'خروجی PDF'
