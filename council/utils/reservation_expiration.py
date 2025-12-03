from django.utils import timezone
from datetime import timedelta
from council.models import Reservation


EXPIRATION_MINUTES = 15


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
