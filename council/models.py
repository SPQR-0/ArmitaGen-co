import uuid
from datetime import datetime

from django.conf import settings
from django.db import models
from django.utils.text import slugify


def prescription_upload_path(instance, filename):
    """
    prescriptions/YYYY/MM/user-name/filename
    """

    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")

    user_name = slugify(instance.user.full_name, allow_unicode=True)
    ext = filename.split('.')[-1]
    filename = f"prescription.{ext}"
    return f"prescriptions/{year}/{month}/{user_name}/{filename}"


class ServiceType(models.Model):
    """Types of services offered"""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    duration = models.PositiveIntegerField(help_text='مدت زمان به دقیقه')
    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveIntegerField(default=0, help_text='ترتیب نمایش')
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'service_types'
        verbose_name = 'نوع خدمت'
        verbose_name_plural = 'انواع خدمات'
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['slug'], name='idx_service_slug'),
            models.Index(fields=['is_active'], name='idx_service_active'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class SlotRule(models.Model):
    """Rules for automatic slot generation"""

    WEEKDAY_CHOICES = [
        (0, 'شنبه'),
        (1, 'یکشنبه'),
        (2, 'دوشنبه'),
        (3, 'سه‌شنبه'),
        (4, 'چهارشنبه'),
        (5, 'پنج‌شنبه'),
        (6, 'جمعه'),
    ]

    weekdays = models.CharField(
        max_length=20,
        help_text='روزهای هفته با کاما جدا شده: 0,1,2,3,4'
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    interval_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'slot_rules'
        verbose_name = 'قانون بازه زمانی'
        verbose_name_plural = 'قوانین بازه‌های زمانی'

    def __str__(self):
        return f"{self.start_time} - {self.end_time} (هر {self.interval_minutes} دقیقه)"

    def get_weekdays_list(self):
        return [int(d) for d in self.weekdays.split(',')]


class TimeSlot(models.Model):
    """Available time slots for reservations"""

    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_slots'
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'time_slots'
        verbose_name = 'بازه زمانی'
        verbose_name_plural = 'بازه‌های زمانی'
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['date'], name='idx_slot_date'),
            models.Index(fields=['date', 'start_time'], name='idx_time_lookup'),
            models.Index(fields=['date', 'is_available'], name='idx_available_slots'),
        ]

    def __str__(self):
        return f"{self.date} | {self.start_time} - {self.end_time}"


class Reservation(models.Model):
    """User reservations"""

    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('confirmed', 'تایید شده'),
        ('cancelled', 'لغو شده'),
        ('completed', 'انجام شده'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations'
    )
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.PROTECT,
        related_name='reservations'
    )
    time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.PROTECT,
        related_name='reservations'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    reserved_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(null=True, blank=True)
    prescription = models.FileField(
        upload_to=prescription_upload_path,
        null=True,
        blank=True
    )
    confirmation_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reservations'
        verbose_name = 'رزرو'
        verbose_name_plural = 'رزروها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='idx_reservation_user'),
            models.Index(fields=['status'], name='idx_reservation_status'),
            models.Index(fields=['confirmation_code'], name='idx_confirmation_code'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'time_slot'],
                name='idx_unique_user_slot'
            )
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.confirmation_code}"

    def save(self, *args, **kwargs):
        if not self.confirmation_code:
            self.confirmation_code = str(uuid.uuid4())[:10].upper()
        super().save(*args, **kwargs)
