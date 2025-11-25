import os

from django.core.exceptions import ValidationError
from django.db import models


def validate_file_size(value):
    limit = 5 * 1024 * 1024  # 5 MB
    if value.size > limit:
        raise ValidationError("حجم فایل نباید بیشتر از 5 مگابایت باشد.")


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
    if ext not in valid_extensions:
        raise ValidationError('فقط فایل‌های PDF و تصویر (JPG, PNG) مجاز هستند.')


class GeneticConsultationRequest(models.Model):
    SERVICE_CHOICES = [
        ('', 'انتخاب خدمت'),  # placeholder
        ('سرطان', 'آزمایشگاه سرطان'),
        ('مادر_جنین', 'آزمایشگاه سلامت مادر و جنین'),
        ('مولکولی', 'ژنتیک مولکولی'),
        ('سایر', 'سایر خدمات'),
    ]

    full_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی")
    phone_number = models.CharField(max_length=15, verbose_name="شماره تلفن")
    prescription_file = models.FileField(
        upload_to='consultation_prescriptions/',
        null=True,
        blank=True,
        verbose_name="آپلود نسخه/مدارک",
        validators=[validate_file_size, validate_file_extension]
    )
    service_type = models.CharField(
        max_length=100,
        choices=SERVICE_CHOICES,
        default='',
        verbose_name="نوع خدمت درخواستی"
    )
    message = models.TextField(verbose_name="پیام یا توضیحات تکمیلی")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "درخواست مشاوره ژنتیک"
        verbose_name_plural = "درخواست‌های مشاوره ژنتیک"
        ordering = ['-created_at']

    def __str__(self):
        return f"درخواست مشاوره از طرف: {self.full_name}"
