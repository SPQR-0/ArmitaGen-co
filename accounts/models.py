import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
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
    full_name = models.CharField(max_length=255, verbose_name='نام و نام خانوادگی')
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
        # if not self.is_expired():
        #     return False
        return timezone.now() > self.expires_at

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
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
