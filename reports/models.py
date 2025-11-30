from django.db import models
from django.conf import settings


class Report(models.Model):
    """Generic reports for different entities"""

    TYPE_CHOICES = [
        ('reservation', 'گزارش رزرو'),
        ('user', 'گزارش کاربر'),
        ('payment', 'گزارش پرداخت'),
        ('system', 'گزارش سیستم'),
    ]

    type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    related_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='ID مرتبط با نوع گزارش'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_reports'
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_visible_to_user = models.BooleanField(
        default=False,
        help_text='آیا کاربر می‌تواند این گزارش را ببیند؟'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reports'
        verbose_name = 'گزارش'
        verbose_name_plural = 'گزارش‌ها'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['type'], name='idx_report_type'),
            models.Index(fields=['type', 'related_id'], name='idx_report_relation'),
            models.Index(fields=['created_by'], name='idx_report_creator'),
        ]

    def __str__(self):
        return f"{self.get_type_display()} - {self.title}"