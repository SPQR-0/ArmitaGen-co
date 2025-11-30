from django.db import models

from council.models import Reservation


class Payment(models.Model):
    """Payment records"""

    STATUS_CHOICES = [
        ('pending', 'در انتظار پرداخت'),
        ('success', 'موفق'),
        ('failed', 'ناموفق'),
        ('refunded', 'بازگشت داده شده'),
    ]

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )

    reference_code = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text='کد رهگیری درگاه پرداخت'
    )

    tracking_code = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text='کد پیگیری بانک - برای نمایش به کاربر'
    )

    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reservation'], name='idx_payment_reservation'),
            models.Index(fields=['status'], name='idx_payment_status'),
            models.Index(fields=['reference_code'], name='idx_payment_reference'),
        ]

    def __str__(self):
        return f"Payment #{self.id} - {self.get_status_display()}"

    def is_paid(self):
        """آیا پرداخت موفق بوده؟"""
        return self.status == 'success' and self.tracking_code is not None
