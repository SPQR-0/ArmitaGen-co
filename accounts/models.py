import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom manager for User model without username"""

    def create_user(self, phone, full_name, password=None, **extra_fields):
        """Create and return a regular user"""
        if not phone:
            raise ValueError('Phone number is required')
        if not full_name:
            raise ValueError('Full name is required')

        user = self.model(
            phone=phone,
            full_name=full_name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, full_name, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('otp_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(phone, full_name, password, **extra_fields)


class User(AbstractUser):
    """Custom User model with phone-first authentication"""

    phone = models.CharField(max_length=15, unique=True, db_index=True, verbose_name='تلفن')
    email = models.EmailField(unique=False, null=True, blank=True, verbose_name='ایمیل')
    full_name = models.CharField(max_length=50, verbose_name='نام و نام خانوادگی')
    otp_verified = models.BooleanField(default=False, verbose_name='تایید کد پیامکی')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    # Remove username requirement
    username = None
    objects = UserManager()  # Custom Manager
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'
        indexes = [
            models.Index(fields=['phone'], name='idx_phone'),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"


class OTP(models.Model):
    """One-Time Password for phone verification"""

    phone = models.CharField(max_length=15, db_index=True, verbose_name='شماره تلفن')
    code = models.CharField(max_length=6, verbose_name='کد')
    is_used = models.BooleanField(default=False, verbose_name='استفاده شده')
    verified_user = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='otps',
        verbose_name='کاربر تایید شده'
    )
    expires_at = models.DateTimeField(verbose_name='تاریخ انقضا')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    class Meta:
        db_table = 'otps'
        verbose_name = 'OTP'
        verbose_name_plural = 'OTP ها'
        indexes = [
            models.Index(fields=['phone'], name='idx_otp_phone'),
            models.Index(fields=['phone', 'code'], name='idx_otp_verify'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.phone} - {self.code}"

    def is_expired(self):
        """Return True if OTP is expired (2 minutes after creation)"""
        return timezone.now() > self.created_at + timedelta(minutes=2)

    def mark_as_used(self, user=None):
        self.is_used = True
        if user:
            self.verified_user = user
        self.save(update_fields=["is_used", "verified_user"])

    @classmethod
    def generate_code(cls):
        """Generate cryptographically secure 6-digit OTP"""
        return str(secrets.randbelow(900000) + 100000)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=2)
        super().save(*args, **kwargs)


class UserInfo(models.Model):
    """
    Aggregated user information model
    This model stores computed/cached data about users for reporting and admin purposes
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_info',
        verbose_name='کاربر'
    )

    # Basic Info (cached from User model)
    full_name = models.CharField(
        max_length=255,
        verbose_name='نام و نام خانوادگی'
    )
    phone = models.CharField(
        max_length=15,
        db_index=True,
        verbose_name='شماره تلفن'
    )
    email = models.EmailField(
        null=True,
        blank=True,
        verbose_name='ایمیل'
    )

    # Verification Status
    is_otp_verified = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='تایید شماره با OTP'
    )

    # Activity Tracking
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='آخرین ورود'
    )
    first_reservation_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاریخ اولین رزرو'
    )
    last_reservation_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاریخ آخرین رزرو'
    )

    # Reservation Statistics
    total_reservations = models.PositiveIntegerField(
        default=0,
        verbose_name='تعداد کل رزروها'
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

    # Payment Statistics
    total_payments_sum = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name='مجموع پرداخت‌ها (تومان)'
    )
    successful_payments_count = models.PositiveIntegerField(
        default=0,
        verbose_name='تعداد پرداخت‌های موفق'
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخرین بروزرسانی'
    )

    class Meta:
        db_table = 'user_info'
        verbose_name = 'اطلاعات کاربر'
        verbose_name_plural = 'اطلاعات کاربران'
        ordering = ['-last_reservation_date', '-updated_at']
        indexes = [
            models.Index(fields=['phone'], name='idx_userinfo_phone'),
            models.Index(fields=['is_otp_verified'], name='idx_userinfo_verified'),
            models.Index(fields=['last_login'], name='idx_userinfo_login'),
            models.Index(fields=['total_reservations'], name='idx_userinfo_reservations'),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.phone}"

    @classmethod
    def create_or_update_for_user(cls, user):
        """
        Create or update UserInfo for a given user
        This aggregates all data from User and related Reservations
        """
        from council.models import Reservation  # Import here to avoid circular import
        from payments.models import Payment  # Import Payment model

        # Get or create UserInfo
        user_info, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'full_name': user.full_name,
                'phone': user.phone,
                'email': user.email,
                'is_otp_verified': user.otp_verified,
                'last_login': user.last_login,
            }
        )

        # Update basic info
        user_info.full_name = user.full_name
        user_info.phone = user.phone
        user_info.email = user.email
        user_info.is_otp_verified = user.otp_verified
        user_info.last_login = user.last_login

        # Get reservation statistics
        reservations = Reservation.objects.filter(
            user=user,
            deleted_at__isnull=True
        )

        user_info.total_reservations = reservations.count()
        user_info.completed_reservations = reservations.filter(status='completed').count()
        user_info.cancelled_reservations = reservations.filter(status='cancelled').count()
        user_info.pending_reservations = reservations.filter(
            status__in=['pending', 'phone_verified']
        ).count()

        # Get date range
        reservation_dates = reservations.exclude(
            status='cancelled'
        ).order_by('created_at').values_list('created_at', flat=True)

        if reservation_dates:
            user_info.first_reservation_date = reservation_dates.first()
            user_info.last_reservation_date = reservation_dates.last()

        # Calculate payment statistics using Payment model
        successful_payments = Payment.objects.filter(
            reservation__user=user,
            reservation__deleted_at__isnull=True,
            status='success'
        )

        payments_sum = successful_payments.aggregate(
            total=Sum('amount')
        )['total'] or 0

        user_info.total_payments_sum = payments_sum
        user_info.successful_payments_count = successful_payments.count()

        user_info.save()
        return user_info

    def refresh_stats(self):
        """Refresh statistics for this user"""
        return self.__class__.create_or_update_for_user(self.user)

    @property
    def average_payment(self):
        """Calculate average payment amount"""
        if self.successful_payments_count > 0:
            return self.total_payments_sum / self.successful_payments_count
        return 0

    @property
    def completion_rate(self):
        """Calculate reservation completion rate as percentage"""
        if self.total_reservations > 0:
            return round((self.completed_reservations / self.total_reservations) * 100, 1)
        return 0

    @property
    def cancellation_rate(self):
        """Calculate reservation cancellation rate as percentage"""
        if self.total_reservations > 0:
            return round((self.cancelled_reservations / self.total_reservations) * 100, 1)
        return 0

    @property
    def days_since_last_reservation(self):
        """Calculate days since last reservation"""
        if self.last_reservation_date:
            delta = timezone.now() - self.last_reservation_date
            return delta.days
        return None

    @property
    def is_active_user(self):
        """Check if user is active (reserved in last 30 days)"""
        if self.last_reservation_date:
            days_since = self.days_since_last_reservation
            return days_since is not None and days_since <= 30
        return False
