from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver, Signal
from django.utils import timezone

from accounts.models import OTP, User
from council.models import Reservation
from payments.models import Payment
from .models import (
    UserActivity, UserStatistics, ReservationLog,
    PaymentLog
)

# Custom signals
reservation_status_changed = Signal()
payment_status_changed = Signal()


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log user login activity"""
    UserActivity.objects.create(
        user=user,
        action_type='login',
        severity='info',
        description=f'کاربر {user.full_name} وارد سیستم شد',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        device_type=detect_device_type(request),
        browser=detect_browser(request),
        os=detect_os(request),
        metadata={
            'login_time': timezone.now().isoformat(),
            'session_key': request.session.session_key
        }
    )

    # Update statistics
    stats, created = UserStatistics.objects.get_or_create(user=user)
    stats.total_logins += 1
    stats.last_activity = timezone.now()
    if created:
        stats.first_activity = timezone.now()
    stats.save()


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout activity"""
    if user:
        UserActivity.objects.create(
            user=user,
            action_type='logout',
            severity='info',
            description=f'کاربر {user.full_name} از سیستم خارج شد',
            ip_address=get_client_ip(request),
            metadata={
                'logout_time': timezone.now().isoformat()
            }
        )


@receiver(post_save, sender=User)
def log_user_registration(sender, instance, created, **kwargs):
    """Log new user registration"""
    if created:
        UserActivity.objects.create(
            user=instance,
            action_type='registration',
            severity='info',
            description=f'کاربر جدید ثبت‌نام کرد: {instance.full_name}',
            metadata={
                'phone': instance.phone,
                'email': instance.email or '',
                'registration_time': timezone.now().isoformat()
            }
        )

        # Create statistics record
        UserStatistics.objects.create(
            user=instance,
            first_activity=timezone.now(),
            last_activity=timezone.now()
        )


@receiver(post_save, sender=OTP)
def log_otp_activity(sender, instance, created, **kwargs):
    """Log OTP request and verification"""
    if created:
        # OTP requested
        UserActivity.objects.create(
            user=instance.verified_user,
            session_key=instance.phone if not instance.verified_user else None,
            action_type='otp_request',
            severity='info',
            description=f'درخواست کد OTP برای شماره {instance.phone}',
            metadata={
                'phone': instance.phone,
                'code': '******',  # Never log actual OTP code
                'expires_at': instance.expires_at.isoformat()
            }
        )
    elif instance.is_used and instance.verified_user:
        # OTP verified
        UserActivity.objects.create(
            user=instance.verified_user,
            action_type='otp_verify',
            severity='info',
            description=f'کد OTP با موفقیت تایید شد برای {instance.phone}',
            metadata={
                'phone': instance.phone,
                'verified_at': timezone.now().isoformat()
            }
        )


@receiver(pre_save, sender=Reservation)
def log_reservation_status_change(sender, instance, **kwargs):
    """Log reservation status changes"""
    if instance.pk:
        try:
            old_instance = Reservation.objects.get(pk=instance.pk)

            # Check if status changed
            if old_instance.status != instance.status:
                ReservationLog.objects.create(
                    reservation=instance,
                    user=instance.user,
                    old_status=old_instance.status,
                    new_status=instance.status,
                    changed_by=instance.user,
                    change_reason=f'تغییر وضعیت از {old_instance.get_status_display()} به {instance.get_status_display()}',
                    metadata={
                        'old_status_display': old_instance.get_status_display(),
                        'new_status_display': instance.get_status_display(),
                        'changed_at': timezone.now().isoformat()
                    }
                )

                # Log user activity
                UserActivity.objects.create(
                    user=instance.user,
                    action_type='reservation_' + ('cancelled' if instance.status == 'cancelled' else 'created'),
                    severity='warning' if instance.status == 'cancelled' else 'info',
                    description=f'وضعیت رزرو {instance.tracking_code} تغییر کرد',
                    content_type=ContentType.objects.get_for_model(instance),
                    object_id=instance.pk,
                    metadata={
                        'tracking_code': instance.tracking_code,
                        'old_status': old_instance.status,
                        'new_status': instance.status,
                        'service_type': instance.service_type.name,
                        'time_slot': str(instance.time_slot)
                    }
                )
        except Reservation.DoesNotExist:
            pass


@receiver(post_save, sender=Reservation)
def log_reservation_created(sender, instance, created, **kwargs):
    """Log new reservation creation"""
    if created:
        UserActivity.objects.create(
            user=instance.user,
            session_key=instance.phone_number if not instance.user else None,
            action_type='reservation_start',
            severity='info',
            description=f'رزرو جدید ایجاد شد: {instance.tracking_code}',
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.pk,
            metadata={
                'tracking_code': instance.tracking_code,
                'service_type': instance.service_type.name,
                'service_price': str(instance.service_type.price),
                'time_slot_date': str(instance.time_slot.date),
                'time_slot_time': f"{instance.time_slot.start_time} - {instance.time_slot.end_time}",
                'full_name': instance.full_name,
                'phone_number': instance.phone_number
            }
        )

        # Create initial reservation log
        ReservationLog.objects.create(
            reservation=instance,
            user=instance.user,
            new_status='created',
            change_reason='ایجاد رزرو جدید',
            metadata={
                'created_at': timezone.now().isoformat(),
                'initial_status': instance.status
            }
        )

        # Update user statistics
        if instance.user:
            stats, _ = UserStatistics.objects.get_or_create(user=instance.user)
            stats.total_reservations += 1
            stats.pending_reservations += 1
            stats.last_reservation = timezone.now()
            stats.last_activity = timezone.now()
            stats.save()


@receiver(post_save, sender=Payment)
def log_payment_activity(sender, instance, created, **kwargs):
    """Log payment transactions and update statistics"""

    transaction_type = 'init' if created else instance.status

    description = f"{'شروع' if created else 'پرداخت'} پرداخت برای رزرو {instance.reservation.tracking_code}"

    # مقادیر امن
    safe_gateway = getattr(instance, 'gateway', None) or getattr(instance, 'gateway_name', None) or 'zarinpal'
    safe_authority = getattr(instance, 'reference_code', None)
    safe_ref_id = getattr(instance, 'tracking_code', None)

    # ایجاد PaymentLog
    PaymentLog.objects.create(
        payment=instance,
        reservation=instance.reservation,
        user=instance.reservation.user,
        transaction_type=transaction_type,
        amount=instance.amount,
        gateway_name=safe_gateway,
        gateway_status=instance.status,
        gateway_message=None,
        authority=safe_authority,
        ref_id=safe_ref_id,
        request_data={},
        response_data={},
        ip_address=None
    )

    # UserActivity logging
    action_type = 'payment_init' if created else (
        'payment_success' if instance.status == 'success' else 'payment_failed')
    severity = 'info' if instance.status == 'success' else 'warning'

    UserActivity.objects.create(
        user=instance.reservation.user,
        action_type=action_type,
        severity=severity,
        description=description,
        content_type=ContentType.objects.get_for_model(instance),
        object_id=instance.pk,
        metadata={
            'payment_id': instance.id,
            'reservation_code': instance.reservation.tracking_code,
            'amount': str(instance.amount),
            'status': instance.status,
            'gateway': safe_gateway,
            'ref_id': safe_ref_id
        }
    )

    # ✅ FIX: Update UserStatistics for payment
    if instance.reservation.user:
        stats, _ = UserStatistics.objects.get_or_create(user=instance.reservation.user)

        if not created:  # Only update stats when payment status changes (not on creation)
            if instance.status == 'success':
                # Add payment amount to total
                stats.total_payments = (stats.total_payments or 0) + int(instance.amount)
                stats.successful_payments = (stats.successful_payments or 0) + 1
                stats.last_payment = timezone.now()

            elif instance.status == 'failed':
                stats.failed_payments = (stats.failed_payments or 0) + 1

            stats.last_activity = timezone.now()
            stats.save()


@receiver(post_save, sender=Reservation)
def update_reservation_statistics(sender, instance, created, **kwargs):
    """Update statistics when reservation status changes"""
    if not created and instance.user:
        stats, _ = UserStatistics.objects.get_or_create(user=instance.user)

        if instance.status == 'completed':
            stats.completed_reservations += 1
            stats.pending_reservations = max(0, stats.pending_reservations - 1)
        elif instance.status == 'cancelled':
            stats.cancelled_reservations += 1
            stats.pending_reservations = max(0, stats.pending_reservations - 1)

        stats.last_activity = timezone.now()
        stats.save()


# Helper functions
def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def detect_device_type(request):
    """Detect device type from user agent"""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()

    if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
        return 'mobile'
    elif 'tablet' in user_agent or 'ipad' in user_agent:
        return 'tablet'
    else:
        return 'desktop'


def detect_browser(request):
    """Detect browser from user agent"""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()

    if 'chrome' in user_agent and 'edg' not in user_agent:
        return 'Chrome'
    elif 'safari' in user_agent and 'chrome' not in user_agent:
        return 'Safari'
    elif 'firefox' in user_agent:
        return 'Firefox'
    elif 'edg' in user_agent:
        return 'Edge'
    elif 'opera' in user_agent or 'opr' in user_agent:
        return 'Opera'
    else:
        return 'Unknown'


def detect_os(request):
    """Detect OS from user agent"""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()

    if 'windows' in user_agent:
        return 'Windows'
    elif 'mac' in user_agent:
        return 'macOS'
    elif 'linux' in user_agent:
        return 'Linux'
    elif 'android' in user_agent:
        return 'Android'
    elif 'iphone' in user_agent or 'ipad' in user_agent:
        return 'iOS'
    else:
        return 'Unknown'