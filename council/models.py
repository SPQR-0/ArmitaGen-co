# app_name/models.py

from django.db import models

class GeneticConsultationRequest(models.Model):
    # اطلاعات بیمار
    full_name = models.CharField(max_length=150, verbose_name="نام و نام خانوادگی")
    phone_number = models.CharField(max_length=15, verbose_name="شماره تلفن")

    # فیلد آپلود فایل برای نسخه (prescription)
    prescription_file = models.FileField(
        upload_to='consultation_prescriptions/',
        null=True, # اجازه خالی بودن فیلد رو می‌دهیم (اگر آپلود نسخه اختیاری است)
        blank=True,
        verbose_name="آپلود نسخه/مدارک"
    )

    # اطلاعات مشاوره
    service_type = models.CharField(max_length=100, verbose_name="نوع خدمت درخواستی")
    message = models.TextField(verbose_name="پیام یا توضیحات تکمیلی")
    
    # زمان و تاریخ ثبت درخواست
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "درخواست مشاوره ژنتیک"
        verbose_name_plural = "درخواست‌های مشاوره ژنتیک"

    def __str__(self):
        return f"درخواست مشاوره از طرف: {self.full_name}"