from django.db import models
from django.conf import settings


class Report(models.Model):
    """
    Generic reports for different entities
    Can be used for reservation reports, user reports, payment reports, etc.
    """

    TYPE_CHOICES = [
        ('reservation', 'گزارش رزرو'),
        ('user', 'گزارش کاربر'),
        ('payment', 'گزارش پرداخت'),
        ('system', 'گزارش سیستم'),
    ]

    # Report metadata
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        db_index=True,
        verbose_name='نوع گزارش',
        help_text='نوع موجودیتی که گزارش درباره آن است'
    )
    related_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='شناسه مرتبط',
        help_text='شناسه رکورد مرتبط (مثلاً ID رزرو یا کاربر)'
    )

    # Report content
    title = models.CharField(
        max_length=255,
        verbose_name='عنوان گزارش'
    )
    content = models.TextField(
        verbose_name='محتوای گزارش',
        help_text='متن کامل گزارش'
    )

    # Permissions
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_reports',
        verbose_name='ایجادکننده',
        help_text='کاربری که این گزارش را ایجاد کرده است'
    )
    is_visible_to_user = models.BooleanField(
        default=False,
        verbose_name='قابل مشاهده برای کاربر',
        help_text='آیا کاربر می‌تواند این گزارش را مشاهده کند؟'
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='تاریخ بروزرسانی'
    )

    class Meta:
        db_table = 'reports'
        verbose_name = 'گزارش'
        verbose_name_plural = 'گزارش‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['type'], name='idx_report_type'),
            models.Index(fields=['type', 'related_id'], name='idx_report_relation'),
            models.Index(fields=['created_by'], name='idx_report_creator'),
            models.Index(fields=['is_visible_to_user'], name='idx_report_visibility'),
        ]

    def __str__(self):
        return f"{self.get_type_display()} - {self.title}"

    def get_related_object(self):
        """
        Get the related object based on type and related_id
        Returns None if not found or type is not supported
        """
        if not self.related_id:
            return None

        try:
            if self.type == 'reservation':
                from council.models import Reservation
                return Reservation.objects.get(id=self.related_id)
            elif self.type == 'user':
                from accounts.models import User
                return User.objects.get(id=self.related_id)
            elif self.type == 'payment':
                from payments.models import Payment
                return Payment.objects.get(id=self.related_id)
        except Exception:
            return None

        return None