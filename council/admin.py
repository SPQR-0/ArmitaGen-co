from datetime import datetime, timedelta

from django.contrib import admin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html

from .models import ServiceType, SlotRule, TimeSlot, Reservation


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'duration', 'active_badge', 'order']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Pricing & Duration', {
            'fields': ('price', 'duration')
        }),
        ('Settings', {
            'fields': ('is_active', 'order')
        }),
    )

    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 10px; border-radius: 12px;">Active</span>'
            )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 10px; border-radius: 12px;">Inactive</span>'
        )

    active_badge.short_description = 'Status'


@admin.register(SlotRule)
class SlotRuleAdmin(admin.ModelAdmin):
    list_display = ['time_range', 'interval_display', 'weekdays_display', 'active_badge']
    list_filter = ['is_active', 'created_at']

    def time_range(self, obj):
        return f"{obj.start_time} - {obj.end_time}"

    time_range.short_description = 'Time Range'

    def interval_display(self, obj):
        return f"{obj.interval_minutes} min"

    interval_display.short_description = 'Interval'

    def weekdays_display(self, obj):
        days = ['Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        selected = [days[int(d)] for d in obj.weekdays.split(',')]
        return ', '.join(selected)

    weekdays_display.short_description = 'Weekdays'

    def active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: gray;">✗ Inactive</span>')

    active_badge.short_description = 'Status'


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['date', 'time_range', 'availability_badge', 'created_by', 'created_at']
    list_filter = ['is_available', 'date', 'created_at']
    search_fields = ['date']
    date_hierarchy = 'date'
    actions = ['bulk_generate_slots']
    change_list_template = 'admin/council/timeslot_changelist.html'

    # Custom URLs for bulk generation
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-generate/', self.admin_site.admin_view(self.bulk_generate_view), name='timeslot_bulk_generate'),
        ]
        return custom_urls + urls

    def bulk_generate_view(self, request):
        """Bulk slot generation view"""
        if request.method == 'POST':
            # Get form data
            start_date = datetime.strptime(request.POST['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.POST['end_date'], '%Y-%m-%d').date()
            start_time = datetime.strptime(request.POST['start_time'], '%H:%M').time()
            end_time = datetime.strptime(request.POST['end_time'], '%H:%M').time()
            interval = int(request.POST['interval'])
            exclude_dates = request.POST.get('exclude_dates', '').strip()

            # Parse excluded dates
            excluded = []
            if exclude_dates:
                for date_str in exclude_dates.split(','):
                    try:
                        excluded.append(datetime.strptime(date_str.strip(), '%Y-%m-%d').date())
                    except ValueError:
                        pass

            # Generate slots
            created_count = 0
            current_date = start_date

            while current_date <= end_date:
                # Skip excluded dates
                if current_date in excluded:
                    current_date += timedelta(days=1)
                    continue

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
                        date=current_date,
                        start_time=current_time,
                        end_time=slot_end,
                        defaults={
                            'is_available': True,
                            'created_by': request.user
                        }
                    )

                    if created:
                        created_count += 1

                    # Move to next slot
                    current_time = slot_end

                current_date += timedelta(days=1)

            messages.success(request, f'{created_count} time slots created successfully!')
            return redirect('admin:council_timeslot_changelist')

        # GET request - show form
        context = {
            'title': 'Bulk Generate Time Slots',
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        return render(request, 'admin/council/timeslot_bulk_generate.html', context)

    def bulk_generate_slots(self, request, queryset):
        """Redirect to bulk generation page"""
        return redirect('admin:timeslot_bulk_generate')

    bulk_generate_slots.short_description = 'Bulk generate time slots'

    def time_range(self, obj):
        return f"{obj.start_time} - {obj.end_time}"

    time_range.short_description = 'Time'

    def availability_badge(self, obj):
        if obj.is_available:
            return format_html('<span style="color: green;">✓ Available</span>')
        return format_html('<span style="color: red;">✗ Reserved</span>')

    availability_badge.short_description = 'Status'


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'confirmation_code',
        'user_link',
        'service_type',
        'slot_info',
        'status_badge',
        'created_at'
    ]
    list_filter = ['status', 'created_at', 'service_type']
    search_fields = [
        'confirmation_code',
        'user__phone',
        'user__full_name'
    ]
    readonly_fields = ['confirmation_code', 'reserved_at', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Reservation Info', {
            'fields': ('user', 'service_type', 'time_slot', 'status')
        }),
        ('Details', {
            'fields': ('message', 'prescription', 'confirmation_code')
        }),
        ('Timestamps', {
            'fields': ('reserved_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        url = f'/admin/accounts/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.full_name)

    user_link.short_description = 'User'

    def slot_info(self, obj):
        return f"{obj.time_slot.date} | {obj.time_slot.start_time}"

    slot_info.short_description = 'Slot'

    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'confirmed': '#28a745',
            'cancelled': '#dc3545',
            'completed': '#17a2b8',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display().upper()
        )

    status_badge.short_description = 'Status'
