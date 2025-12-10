from datetime import timedelta

import pytz
from django.db import models
from django.utils import timezone

from council.models import Reservation, TimeSlot

EXPIRATION_MINUTES = 60
EXPIRATION_SLOT_DAY = 1

def release_expired_reservations():
    """
    Cancels unpaid reservations that passed verification > 15 minutes ago
    and releases their time slots.
    Returns (cancelled_count, released_slots_count)
    """

    cutoff_time = timezone.now() - timedelta(minutes=EXPIRATION_MINUTES)

    expired_reservations = Reservation.objects.filter(
        status='phone_verified',
        payment_status='unpaid',
        phone_verified_at__lt=cutoff_time,
        deleted_at__isnull=True
    ).select_related('time_slot')

    cancelled_count = 0
    released_slots = 0

    for reservation in expired_reservations:
        # Cancel the reservation
        reservation.status = 'cancelled'
        reservation.save(update_fields=['status'])

        # Release time slot
        if reservation.time_slot:
            reservation.time_slot.is_available = True
            reservation.time_slot.save(update_fields=['is_available'])
            released_slots += 1

        cancelled_count += 1

    return cancelled_count, released_slots


def mark_expired_time_slots():
    """
    Mark slots as expired if they are starting within the next 24 hours (or in the past).
    This prevents them from being shown in the booking interface.
    Returns number of slots marked as expired.
    """

    # Tehran Timezone
    tehran_tz = pytz.timezone('Asia/Tehran')
    now_tehran = timezone.now().astimezone(tehran_tz)

    expiration_deadline = now_tehran + timedelta(days=EXPIRATION_SLOT_DAY)
    deadline_date = expiration_deadline.date()
    deadline_time = expiration_deadline.time()

    # current_date = now_tehran.date()
    # current_time = now_tehran.time()
    expired_slots = TimeSlot.objects.filter(
        is_expired=False,
        deleted_at__isnull=True
    ).filter(
        models.Q(date__lt=deadline_date) |
        models.Q(date=deadline_date, start_time__lte=deadline_time)
    )

    count = expired_slots.count()

    if count > 0:
        print(f"⚠️ Found {count} slots closer than 24h (or past) to mark as expired")

    # Mark them as expired and unavailable
    expired_slots.update(
        is_expired=True,
        is_available=False
    )

    return count


def cleanup_expired_data():
    """
    Main cleanup function that should be called periodically.
    Handles both reservation expiration and time slot expiration.
    Returns tuple: (cancelled_reservations, released_slots, expired_slots)
    """

    # Release expired unpaid reservations
    cancelled, released = release_expired_reservations()

    # Mark expired time slots
    expired = mark_expired_time_slots()

    return cancelled, released, expired

# Import at the end to avoid circular imports
