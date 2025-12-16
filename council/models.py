import uuid
from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def prescription_upload_path(instance, filename):
    """
    Generate upload path for prescription files
    Format: prescriptions/YYYY/MM/user-name/filename
    """
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")

    user_name = slugify(instance.full_name, allow_unicode=True)
    ext = filename.split('.')[-1]
    filename = f"prescription.{ext}"
    return f"prescriptions/{year}/{month}/{user_name}/{filename}"


class ConsultationTopic(models.Model):
    """
    موضوعات مشاوره - Topics for consultation
    """
    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='عنوان',
        help_text='مثال: مشاوره تغذیه، مشاوره ورزشی'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        db_index=True,
        verbose_name='شناسه URL'
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name='توضیحات'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='فعال'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='ترتیب نمایش'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )

    class Meta:
        db_table = 'consultation_topics'
        verbose_name = 'موضوع مشاوره'
        verbose_name_plural = 'موضوعات مشاوره'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class ServiceType(models.Model):
    """
    Types of consultation services offered
    e.g., Online, Phone, Text, In-person consultations
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='نام سرویس',
        help_text='یک نام برای نوع مشاوره یا سرویس ارائه کنید'
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name='شناسه URL'
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name='توضیحات'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        verbose_name='قیمت (تومان)'
    )
    duration = models.PositiveIntegerField(
        verbose_name='مدت زمان (دقیقه)',
        help_text='مدت زمان مشاوره به دقیقه'
    )
    is_online = models.BooleanField(
        default=True,
        verbose_name='غیرحضوری',
        help_text='آیا این سرویس به صورت غیرحضوری ارائه می‌شود؟'
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='فعال'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='ترتیب نمایش',
        help_text='ترتیب نمایش در لیست'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاریخ حذف'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )

    class Meta:
        db_table = 'service_types'
        verbose_name = 'نوع سرویس'
        verbose_name_plural = 'انواع سرویس ها'
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['slug'], name='idx_service_slug'),
            models.Index(fields=['is_active'], name='idx_service_active'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-generate slug from name if not provided
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


class SlotRule(models.Model):
    """
    Rules for automatic time slot generation
    Defines patterns like: "Every Saturday 9-13" or "Monday/Wednesday 8-12"
    """

    WEEKDAY_CHOICES = [
        (0, 'شنبه'),
        (1, 'یکشنبه'),
        (2, 'دوشنبه'),
        (3, 'سه‌شنبه'),
        (4, 'چهارشنبه'),
        (5, 'پنج‌شنبه'),
        (6, 'جمعه'),
    ]

    name = models.CharField(
        max_length=100,
        verbose_name='نام الگو',
        help_text='مثال: برنامه حضوری پاییز 1403'
    )
    service_type = models.ForeignKey(
        'ServiceType',
        on_delete=models.CASCADE,
        related_name='slot_rules',
        verbose_name='نوع مشاوره'
    )
    weekdays = models.CharField(
        max_length=20,
        verbose_name='روزهای هفته',
        help_text='روزهای هفته با کاما جدا شده: 0,1,2,3,4'
    )
    start_time = models.TimeField(
        verbose_name='زمان شروع'
    )
    end_time = models.TimeField(
        verbose_name='زمان پایان'
    )
    slot_duration = models.PositiveIntegerField(
        default=60,
        verbose_name='مدت هر نوبت (دقیقه)',
        help_text='مدت زمان هر نوبت به دقیقه'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='فعال'
    )
    apply_from_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='تاریخ شروع اعمال',
        help_text='از چه تاریخی این الگو اعمال شود (اختیاری)'
    )
    apply_to_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='تاریخ پایان اعمال',
        help_text='تا چه تاریخی این الگو اعمال شود (اختیاری)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاریخ بروزرسانی'
    )

    class Meta:
        db_table = 'slot_rules'
        verbose_name = 'الگو بازه زمانی'
        verbose_name_plural = 'الگو های بازه‌های زمانی'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.start_time} تا {self.end_time}"

    def get_weekdays_list(self):
        """Convert comma-separated weekdays string to list of integers"""
        return [int(d) for d in self.weekdays.split(',') if d.strip()]


class TimeSlot(models.Model):
    """
    Available time slots for reservations
    Can be created manually or automatically from SlotRule
    """

    service_type = models.ForeignKey(
        'ServiceType',
        on_delete=models.CASCADE,
        related_name='time_slots',
        verbose_name='نوع مشاوره'
    )
    date = models.DateField(
        db_index=True,
        verbose_name='تاریخ'
    )
    start_time = models.TimeField(
        verbose_name='زمان شروع'
    )
    end_time = models.TimeField(
        verbose_name='زمان پایان'
    )
    is_available = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='در دسترس',
        help_text='آیا این نوبت قابل رزرو است؟'
    )
    is_expired = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='منقضی شده',
        help_text='آیا زمان این نوبت گذشته است؟'
    )
    created_from_rule = models.ForeignKey(
        'SlotRule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_slots',
        verbose_name='ایجاد شده از الگو'
    )
    is_manual = models.BooleanField(
        default=False,
        verbose_name='ایجاد دستی',
        help_text='آیا این نوبت به صورت دستی ایجاد شده است؟'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_slots',
        verbose_name='ایجادکننده'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاریخ حذف'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )

    class Meta:
        db_table = 'time_slots'
        verbose_name = 'بازه زمانی'
        verbose_name_plural = 'بازه‌های زمانی'
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['date'], name='idx_slot_date'),
            models.Index(fields=['date', 'start_time'], name='idx_time_lookup'),
            models.Index(fields=['date', 'is_available'], name='idx_available_slots'),
            models.Index(fields=['service_type'], name='idx_slot_service'),
            models.Index(fields=['is_expired'], name='idx_slot_expired'),
        ]
        constraints = [
            # Prevent duplicate slots for same service at same time
            models.UniqueConstraint(
                fields=['service_type', 'date', 'start_time'],
                name='unique_service_datetime'
            )
        ]

    def __str__(self):
        return f"{self.service_type.name} - {self.date} | {self.start_time} - {self.end_time}"

    def check_and_mark_expired(self):
        """
        Check if this slot has passed and mark as expired
        Returns True if marked as expired, False otherwise
        """

        settings_obj = ReservationSettings.active()
        expiration_days = settings_obj.expiration_slot_day if settings_obj else 1

        tehran_tz = pytz.timezone('Asia/Tehran')
        now = timezone.now().astimezone(tehran_tz)

        slot_datetime = tehran_tz.localize(
            datetime.combine(self.date, self.start_time)
        )

        expiration_deadline = slot_datetime - timedelta(days=expiration_days)

        if now >= expiration_deadline and not self.is_expired:
            self.is_expired = True
            self.is_available = False
            self.save(update_fields=['is_expired', 'is_available'])
            return True

        return False


class Reservation(models.Model):
    """
    User reservations for consultation appointments
    Handles the complete booking flow: creation -> OTP -> payment -> completion
    """

    STATUS_CHOICES = [
        ('pending', 'در انتظار تایید شماره'),
        ('phone_verified', 'شماره تایید شده - در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('completed', 'انجام شده'),
        ('cancelled', 'لغو شده'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'پرداخت نشده'),
        ('paid', 'پرداخت شده'),
        ('refunded', 'بازگشت داده شده'),
    ]

    # Tracking
    tracking_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        verbose_name='کد پیگیری',
        help_text='کد یکتای رزرو برای پیگیری'
    )

    # Relations
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations',
        verbose_name='کاربر',
        help_text='پس از تایید OTP، کاربر مرتبط می‌شود'
    )
    service_type = models.ForeignKey(
        'ServiceType',
        on_delete=models.PROTECT,
        related_name='reservations',
        verbose_name='نوع مشاوره'
    )
    time_slot = models.ForeignKey(
        'TimeSlot',
        on_delete=models.PROTECT,
        related_name='reservations',
        verbose_name='بازه زمانی'
    )
    consultation_topic = models.ForeignKey(
        'ConsultationTopic',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations',
        verbose_name='عنوان مشاوره',
        help_text='موضوع اصلی مشاوره'
    )

    # Contact Information (collected before OTP verification)
    full_name = models.CharField(
        max_length=50,
        verbose_name='نام و نام خانوادگی'
    )
    phone_number = models.CharField(
        max_length=15,
        db_index=True,
        verbose_name='شماره تلفن'
    )
    email = models.EmailField(
        null=True,
        blank=True,
        verbose_name='ایمیل'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name='وضعیت'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid',
        verbose_name='وضعیت پرداخت'
    )
    phone_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='زمان تایید شماره'
    )

    # Additional info
    message = models.TextField(
        null=True,
        blank=True,
        verbose_name='پیام و توضیحات',
        help_text='یادداشت یا توضیحات کاربر'
    )
    prescription = models.FileField(
        upload_to=prescription_upload_path,
        null=True,
        blank=True,
        verbose_name='نسخه پزشک',
        help_text='فایل نسخه (در صورت نیاز)'
    )

    # Timestamps
    reserved_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='زمان رزرو'
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاریخ حذف'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاریخ بروزرسانی'
    )

    class Meta:
        db_table = 'reservations'
        verbose_name = 'رزرو'
        verbose_name_plural = 'رزروها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='idx_reservation_user'),
            models.Index(fields=['status'], name='idx_reservation_status'),
            models.Index(fields=['tracking_code'], name='idx_tracking_code'),
            models.Index(fields=['phone_number'], name='idx_reservation_phone'),
        ]

    def __str__(self):
        full_name = f"{self.full_name}"
        return f"{full_name} - {self.tracking_code}"

    def save(self, *args, **kwargs):
        # Auto-generate tracking code if not exists
        if not self.tracking_code:
            self.tracking_code = f"RES-{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def full_name_display(self):
        """Get full name of person who made reservation"""
        return f"{self.full_name}"

    def is_paid(self):
        """Check if reservation is paid"""
        return self.payment_status == 'paid'

    def can_be_cancelled(self):
        """Check if reservation can be canceled"""
        return self.status in ['pending', 'phone_verified', 'paid']


class ReservationSettings(models.Model):
    is_active = models.BooleanField(
        default=True,
        verbose_name="فعال",
        help_text="در صورت فعال بودن، این تنظیمات به عنوان تنظیمات اصلی سیستم استفاده می‌شود."
    )
    payment_deadline_minutes = models.PositiveIntegerField(
        default=15,
        verbose_name="مهلت پرداخت (دقیقه)",
        help_text="مهلت پرداخت پس از تأیید شماره تلفن (به دقیقه)."
    )
    expiration_deadline_minutes = models.PositiveIntegerField(
        default=60,
        verbose_name="مهلت منقضی شدن نوبت (دقیقه)",
        help_text="مدت زمانی که اگر کاربر پرداخت را انجام ندهد، نوبت به صورت خودکار منقضی می‌شود."
    )
    min_reservable_day = models.PositiveIntegerField(
        default=1,
        verbose_name="حداقل روزهای قابل رزرو",
        help_text="کاربر حداقل چند روز قبل از نوبت می‌تواند رزرو ها را مشاهده کند؟"
    )
    max_reservable_day = models.PositiveIntegerField(
        default=30,
        verbose_name="حداکثر روزهای قابل رزرو",
        help_text="کاربر حداکثر چند روز آینده را می‌تواند رزرو کند؟"
    )
    expiration_slot_day = models.PositiveIntegerField(
        default=1,
        verbose_name="روز منقضی شدن نوبت",
        help_text="چند روز قبل از زمان نوبت باید آن را منقضی و غیرقابل رزرو کرد؟"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاریخ ایجاد"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="آخرین به‌روزرسانی"
    )

    class Meta:
        verbose_name = "تنظیمات رزرو"
        verbose_name_plural = "تنظیمات رزرو"
        ordering = ['-created_at']

    @staticmethod
    def active():
        obj = ReservationSettings.objects.filter(is_active=True).first()
        if not obj:
            # Safe fallback
            obj = ReservationSettings.objects.create(
                is_active=True,
                payment_deadline_minutes=15,
                expiration_deadline_minutes=60,
                min_reservable_day=1,
                max_reservable_day=30,
                expiration_slot_day=1,
            )
        return obj

    def save(self, *args, **kwargs):
        if self.is_active:
            ReservationSettings.objects.exclude(id=self.id).update(is_active=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"تنظیمات فعال: {self.is_active} (حداقل {self.min_reservable_day} روز، حداکثر {self.max_reservable_day} روز)"
