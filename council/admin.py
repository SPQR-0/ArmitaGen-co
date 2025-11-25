from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import GeneticConsultationRequest
from urllib.parse import quote

@admin.register(GeneticConsultationRequest)
class GeneticConsultationRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'full_name_with_icon',
        'phone_number_clickable',
        'service_type_badge',
        'has_prescription',
        'created_at_formatted',
        'action_buttons'
    ]

    list_filter = [
        'service_type',
        'created_at',
        ('prescription_file', admin.EmptyFieldListFilter),
    ]

    search_fields = [
        'full_name',
        'phone_number',
        'service_type',
        'message'
    ]

    ordering = ['-created_at']

    list_per_page = 25

    readonly_fields = [
        'created_at',
        'prescription_preview',
        'download_prescription_button'
    ]

    fieldsets = (
        ('📋 اطلاعات تماس', {
            'fields': ('full_name', 'phone_number')
        }),
        ('💼 جزئیات درخواست', {
            'fields': ('service_type', 'message')
        }),
        ('📎 فایل پیوست', {
            'fields': ('prescription_file', 'prescription_preview', 'download_prescription_button'),
            'classes': ('collapse',),
        }),
        ('⏰ اطلاعات سیستمی', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    actions = ['mark_as_processed', 'export_to_csv']


    @admin.display(description='👤 نام و نام خانوادگی', ordering='full_name')
    def full_name_with_icon(self, obj):
        return format_html(
            '<strong style="color: #2563eb;">{}</strong>',
            obj.full_name
        )

    @admin.display(description='📞 شماره تماس')
    def phone_number_clickable(self, obj):
        return format_html(
            '<a href="tel:{}" style="color: #059669; text-decoration: none;">'
            '<i class="fas fa-phone"></i> {}</a>',
            obj.phone_number,
            obj.phone_number
        )

    @admin.display(description='🏷️ نوع خدمت', ordering='service_type')
    def service_type_badge(self, obj):
        colors = {
            'سرطان': '#dc2626',
            'مادر_جنین': '#059669',
            'مولکولی': '#7c3aed',
            'سایر': '#ea580c',
        }

        color = colors.get(obj.service_type, '#6b7280')
        label = obj.get_service_type_display()

        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 12px; font-weight: bold;">{}</span>',
            color,
            label
        )

    @admin.display(description='📄 نسخه', boolean=True)
    def has_prescription(self, obj):
        return bool(obj.prescription_file)

    @admin.display(description='📅 تاریخ ثبت', ordering='created_at')
    def created_at_formatted(self, obj):
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at

        if diff.days == 0:
            if diff.seconds < 3600:
                time_ago = f'{diff.seconds // 60} دقیقه پیش'
            else:
                time_ago = f'{diff.seconds // 3600} ساعت پیش'
            color = '#dc2626'  # قرمز برای امروز
        elif diff.days == 1:
            time_ago = 'دیروز'
            color = '#ea580c'  # نارنجی
        else:
            time_ago = f'{diff.days} روز پیش'
            color = '#6b7280'  # خاکستری

        return format_html(
            '<span style="color: {}; font-weight: 500;">{}</span><br>'
            '<small style="color: #9ca3af;">{}</small>',
            color,
            time_ago,
            obj.created_at.strftime('%Y/%m/%d - %H:%M')
        )

    @admin.display(description='⚡ عملیات')
    def action_buttons(self, obj):
        buttons = []

        view_url = reverse('admin:council_geneticconsultationrequest_change', args=[obj.pk])
        buttons.append(
            f'<a href="{view_url}" style="background: #2563eb; color: white; padding: 5px 10px; '
            f'border-radius: 4px; text-decoration: none; font-size: 11px; margin-left: 5px;">'
            f'<i class="fas fa-eye"></i> مشاهده</a>'
        )

        # Download btn
        if obj.prescription_file:
            buttons.append(
                f'<a href="{obj.prescription_file.url}" target="_blank" '
                f'style="background: #059669; color: white; padding: 5px 10px; '
                f'border-radius: 4px; text-decoration: none; font-size: 11px; margin-left: 5px;">'
                f'<i class="fas fa-download"></i> نسخه</a>'
            )

        # Call btn
        buttons.append(
            f'<a href="tel:{obj.phone_number}" '
            f'style="background: #7c3aed; color: white; padding: 5px 10px; '
            f'border-radius: 4px; text-decoration: none; font-size: 11px;">'
            f'<i class="fas fa-phone"></i> تماس</a>'
        )

        return format_html(' '.join(buttons))

    @admin.display(description='پیش‌نمایش نسخه')
    def prescription_preview(self, obj):
        if not obj.prescription_file:
            return format_html(
                '<div style="padding: 20px; background: #fee2e2; border-radius: 8px; text-align: center;">'
                '<i class="fas fa-times-circle" style="color: #dc2626; font-size: 24px;"></i><br>'
                '<span style="color: #dc2626; font-weight: bold;">فایلی آپلود نشده است</span>'
                '</div>'
            )

        file_url = obj.prescription_file.url
        file_name = obj.prescription_file.name.split('/')[-1]
        file_ext = file_name.split('.')[-1].lower()

        if file_ext in ['jpg', 'jpeg', 'png']:
            # img preview
            return format_html(
                '<div style="text-align: center;">'
                '<img src="{}" style="max-width: 100%; max-height: 400px; border-radius: 8px; '
                'box-shadow: 0 4px 6px rgba(0,0,0,0.1);" /><br>'
                '<small style="color: #6b7280;">📷 {}</small>'
                '</div>',
                file_url,
                file_name
            )
        elif file_ext == 'pdf':
            # PDF with embed
            return format_html(
                '<div>'
                '<embed src="{}" type="application/pdf" width="100%" height="600px" '
                'style="border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);" /><br>'
                '<small style="color: #6b7280;">📄 {}</small>'
                '</div>',
                file_url,
                file_name
            )
        else:
            return format_html(
                '<div style="padding: 20px; background: #fef3c7; border-radius: 8px; text-align: center;">'
                '<i class="fas fa-file" style="color: #f59e0b; font-size: 24px;"></i><br>'
                '<span style="color: #92400e;">📎 {}</span>'
                '</div>',
                file_name
            )

    @admin.display(description='دانلود فایل')
    def download_prescription_button(self, obj):
        if not obj.prescription_file:
            return '-'

        return format_html(
            '<a href="{}" target="_blank" class="button" '
            'style="background: #059669; color: white; padding: 6px 12px; '
            'border-radius: 6px; text-decoration: none; display: inline-block;">'
            '<i class="fas fa-download"></i> دانلود فایل</a>',
            obj.prescription_file.url
        )

    @admin.action(description='✅ علامت‌گذاری به عنوان پردازش شده')
    def mark_as_processed(self, request, queryset):
        count = queryset.count()
        self.message_user(request, f'{count} درخواست علامت‌گذاری شد.')

    @admin.action(description='📥 خروجی CSV')
    def export_to_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        from django.utils import timezone

        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response[
            'Content-Disposition'] = f'attachment; filename="consultations_{timezone.now().strftime("%Y%m%d")}.csv"'

        writer = csv.writer(response)
        writer.writerow(['شناسه', 'نام', 'تلفن', 'نوع خدمت', 'دارای نسخه', 'تاریخ ثبت'])

        for obj in queryset:
            writer.writerow([
                obj.id,
                obj.full_name,
                obj.phone_number,
                obj.get_service_type_display(),
                'بله' if obj.prescription_file else 'خیر',
                obj.created_at.strftime('%Y/%m/%d %H:%M')
            ])

        return response


    class Media:
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
                'admin/css/custom_admin.css',
            )
        }
