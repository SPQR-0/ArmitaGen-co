from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class UserActivity(models.Model):
    """
    Comprehensive user activity tracking
    Logs all user actions and events
    """

    ACTION_TYPES = [
        ('registration', 'ثبت‌نام'),
        ('login', 'ورود'),
        ('logout', 'خروج'),
        ('otp_request', 'درخواست کد OTP'),
        ('otp_verify', 'تایید کد OTP'),
        ('reservation_start', 'شروع رزرو'),
        ('reservation_created', 'ایجاد رزرو'),
        ('reservation_cancelled', 'لغو رزرو'),
        ('payment_init', 'شروع پرداخت'),
        ('payment_success', 'پرداخت موفق'),
        ('payment_failed', 'پرداخت ناموفق'),
        ('profile_update', 'بروزرسانی پروفایل'),
        ('file_upload', 'آپلود فایل'),
        ('pdf_download', 'دانلود PDF'),
        ('page_view', 'بازدید صفحه'),
        ('error', 'خطا'),
        ('other', 'سایر'),
    ]

    SEVERITY_LEVELS = [
        ('info', 'اطلاعاتی'),
        ('warning', 'هشدار'),
        ('error', 'خطا'),
        ('critical', 'بحرانی'),
    ]

    # User info
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
        verbose_name='کاربر',
        help_text='کاربری که این عملیات را انجام داده'
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name='کلید Session',
        help_text='برای کاربران مهمان (غیر لاگین)'
    )

    # Action details
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_TYPES,
        verbose_name='نوع عملیات'
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='info',
        verbose_name='سطح اهمیت'
    )
    description = models.TextField(
        verbose_name='توضیحات',
        help_text='شرح کامل عملیات انجام شده'
    )

    # Generic relation to any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='نوع محتوا'
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='شناسه شیء'
    )
    related_object = GenericForeignKey('content_type', 'object_id')

    # Additional data (JSON)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='اطلاعات اضافی',
        help_text='داده‌های اضافی به صورت JSON'
    )

    # Request info
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='آدرس IP'
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name='User Agent',
        help_text='مرورگر و سیستم عامل کاربر'
    )
    device_type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='نوع دستگاه',
        help_text='موبایل، تبلت، دسکتاپ'
    )
    browser = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='مرورگر'
    )
    os = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='سیستم عامل'
    )

    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )

    class Meta:
        db_table = 'user_activities'
        verbose_name = 'فعالیت کاربر'
        verbose_name_plural = 'فعالیت‌های کاربران'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='idx_user_activity'),
            models.Index(fields=['action_type', '-created_at'], name='idx_action_time'),
            models.Index(fields=['severity'], name='idx_severity'),
            models.Index(fields=['session_key'], name='idx_session'),
            models.Index(fields=['ip_address'], name='idx_ip'),
        ]

    def __str__(self):
        if self.user:
            user_display = self.user.full_name
        elif self.session_key:
            user_display = f"Session: {self.session_key[:8]}"
        else:
            user_display = "Unknown User/Session"

        return f"{user_display} - {self.get_action_type_display()} - {self.created_at.strftime('%Y/%m/%d %H:%M')}"


class UserStatistics(models.Model):
    """
    Aggregated user statistics
    Updated via signals or periodic tasks
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='statistics',
        verbose_name='کاربر'
    )

    # Reservation stats
    total_reservations = models.PositiveIntegerField(
        default=0,
        verbose_name='مجموع رزروها'
    )
    completed_reservations = models.PositiveIntegerField(
        default=0,
        verbose_name='رزروهای تکمیل شده'
    )
    cancelled_reservations = models.PositiveIntegerField(
        default=0,
        verbose_name='رزروهای لغو شده'
    )
    pending_reservations = models.PositiveIntegerField(
        default=0,
        verbose_name='رزروهای در انتظار'
    )

    # Payment stats
    total_payments = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name='مجموع پرداخت‌ها'
    )
    successful_payments = models.PositiveIntegerField(
        default=0,
        verbose_name='پرداخت‌های موفق'
    )
    failed_payments = models.PositiveIntegerField(
        default=0,
        verbose_name='پرداخت‌های ناموفق'
    )
    refunded_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name='مبلغ بازگشتی'
    )

    # Activity stats
    total_logins = models.PositiveIntegerField(
        default=0,
        verbose_name='تعداد ورود'
    )
    total_activities = models.PositiveIntegerField(
        default=0,
        verbose_name='تعداد فعالیت‌ها'
    )

    # Service usage
    most_used_service = models.ForeignKey(
        'council.ServiceType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='خدمت پرکاربرد'
    )

    # Timestamps
    first_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='اولین فعالیت'
    )
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='آخرین فعالیت'
    )
    last_reservation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='آخرین رزرو'
    )
    last_payment = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='آخرین پرداخت'
    )

    # System fields
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاریخ بروزرسانی'
    )

    class Meta:
        db_table = 'user_statistics'
        verbose_name = 'آمار کاربر'
        verbose_name_plural = 'آمار کاربران'

    def __str__(self):
        return f"آمار {self.user.full_name}"


class ReservationLog(models.Model):
    """
    Detailed reservation lifecycle tracking
    Every state change is logged here
    """

    STATUS_CHANGES = [
        ('created', 'ایجاد شد'),
        ('phone_verified', 'شماره تایید شد'),
        ('payment_pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شد'),
        ('completed', 'تکمیل شد'),
        ('cancelled', 'لغو شد'),
        ('expired', 'منقضی شد'),
    ]

    reservation = models.ForeignKey(
        'council.Reservation',
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='رزرو'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='کاربر'
    )

    # Status change
    old_status = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name='وضعیت قبلی'
    )
    new_status = models.CharField(
        max_length=30,
        choices=STATUS_CHANGES,
        verbose_name='وضعیت جدید'
    )

    # Change details
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservation_changes',
        verbose_name='تغییر توسط',
        help_text='کاربر یا ادمینی که تغییر را ایجاد کرده'
    )
    change_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name='دلیل تغییر'
    )

    # Additional data
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='اطلاعات اضافی'
    )

    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ تغییر'
    )

    class Meta:
        db_table = 'reservation_logs'
        verbose_name = 'لاگ رزرو'
        verbose_name_plural = 'لاگ‌های رزرو'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reservation', '-created_at'], name='idx_res_log'),
            models.Index(fields=['new_status'], name='idx_status_log'),
        ]

    def __str__(self):
        return f"{self.reservation.tracking_code} - {self.get_new_status_display()}"


class PaymentLog(models.Model):
    """
    Detailed logging for payment gateway communication
    """

    TRANSACTION_TYPES = [
        ('init', 'شروع پرداخت'),
        ('redirect', 'هدایت به درگاه'),
        ('callback', 'بازگشت از درگاه'),
        ('verify', 'تایید پرداخت'),
        ('success', 'موفق'),
        ('failed', 'ناموفق'),
        ('refund_request', 'درخواست بازگشت'),
        ('refunded', 'بازگشت داده شد'),
    ]

    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='پرداخت'
    )

    reservation = models.ForeignKey(
        'council.Reservation',
        on_delete=models.CASCADE,
        related_name='payment_logs',
        verbose_name='رزرو'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='کاربر'
    )

    # نوع تراکنش
    transaction_type = models.CharField(
        max_length=30,
        choices=TRANSACTION_TYPES,
        verbose_name='نوع تراکنش'
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name='مبلغ'
    )

    # درگاه پرداخت
    gateway_name = models.CharField(
        max_length=50,
        default='zarinpal',
        verbose_name='نام درگاه'
    )

    # اطلاعات درگاه
    gateway_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='وضعیت درگاه'
    )

    gateway_message = models.TextField(
        null=True,
        blank=True,
        verbose_name='پیام درگاه'
    )

    authority = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Authority'
    )

    ref_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='کد پیگیری'
    )

    # داده‌های درخواست/پاسخ
    request_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='داده‌های درخواست'
    )

    response_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='داده‌های پاسخ'
    )

    # اطلاعات سیستمی
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='آدرس IP'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ تراکنش'
    )

    class Meta:
        db_table = 'payment_logs'
        verbose_name = 'لاگ پرداخت'
        verbose_name_plural = 'لاگ‌های پرداخت'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', '-created_at'], name='idx_pay_log'),
            models.Index(fields=['transaction_type'], name='idx_trans_type'),
            models.Index(fields=['gateway_name'], name='idx_gateway_name'),
        ]

    def __str__(self):
        return f"{self.reservation.tracking_code} - {self.get_transaction_type_display()} - {self.amount:,} تومان"


class ErrorLog(models.Model):
    """
    System errors and exceptions tracking
    """

    ERROR_TYPES = [
        ('validation', 'خطای اعتبارسنجی'),
        ('database', 'خطای دیتابیس'),
        ('payment', 'خطای پرداخت'),
        ('api', 'خطای API'),
        ('server', 'خطای سرور'),
        ('other', 'سایر'),
    ]

    # Error details
    error_type = models.CharField(
        max_length=30,
        choices=ERROR_TYPES,
        verbose_name='نوع خطا'
    )
    error_message = models.TextField(
        verbose_name='پیام خطا'
    )
    stack_trace = models.TextField(
        null=True,
        blank=True,
        verbose_name='Stack Trace'
    )

    # Context
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='کاربر'
    )
    url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='URL'
    )
    view_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='نام View'
    )

    # Request details
    request_method = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='متد درخواست'
    )
    request_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='داده‌های درخواست'
    )

    # System info
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='آدرس IP'
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name='User Agent'
    )

    # Status
    is_resolved = models.BooleanField(
        default=False,
        verbose_name='برطرف شده'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاریخ برطرف شدن'
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_errors',
        verbose_name='برطرف شده توسط'
    )

    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='تاریخ خطا'
    )

    class Meta:
        db_table = 'error_logs'
        verbose_name = 'لاگ خطا'
        verbose_name_plural = 'لاگ‌های خطا'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['error_type', '-created_at'], name='idx_error_type'),
            models.Index(fields=['is_resolved'], name='idx_resolved'),
        ]

    def __str__(self):
        status = "✓ برطرف شده" if self.is_resolved else "✗ فعال"
        return f"{self.get_error_type_display()} - {status} - {self.created_at.strftime('%Y/%m/%d %H:%M')}"
