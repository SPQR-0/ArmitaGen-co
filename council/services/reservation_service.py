from datetime import timedelta, datetime

import pytz
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from payments.models import Payment
from ..models import Reservation, ServiceType, TimeSlot, ConsultationTopic
from ..utils.date_utils import get_jalali_date_info


class ReservationService:
    """Handles all business logic related to the Reservation flow."""

    @staticmethod
    def get_step_one_data(request):
        """Retrieves active Service Types and Consultation Topics for Step 1."""
        service_types = ServiceType.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        ).order_by('order', 'name')

        consultation_topics = ConsultationTopic.objects.filter(
            is_active=True
        ).order_by('order', 'name')

        return service_types, consultation_topics

    @staticmethod
    def get_available_time_slots(service_type_id):
        """
        Retrieves and groups available time slots by date, considering expiration and current time.
        """
        service_type = get_object_or_404(
            ServiceType,
            id=service_type_id,
            is_active=True
        )

        tehran_tz = pytz.timezone('Asia/Tehran')
        now = timezone.now().astimezone(tehran_tz)
        today = now.date()
        current_time = now.time()
        end_date = today + timedelta(days=30)

        # 1. Base query: Active slots within the 30-day window, not expired globally
        available_slots = TimeSlot.objects.filter(
            service_type=service_type,
            date__gte=today,
            date__lte=end_date,
            deleted_at__isnull=True,
            is_expired=False
        ).exclude(
            # 2. Exclude slots that are today but time has already passed
            date=today,
            start_time__lte=current_time
        ).select_related('service_type').order_by('date', 'start_time')

        # 3. Group slots by date and add Jalali info
        slots_by_date = {}
        for slot in available_slots:
            date_key = slot.date.strftime('%Y-%m-%d')

            if date_key not in slots_by_date:
                jalali_info = get_jalali_date_info(slot.date)
                slots_by_date[date_key] = {
                    'date': slot.date,
                    'jalali_date': jalali_info['jalali_date'],
                    'jalali_str': jalali_info['jalali_str'],
                    'weekday': jalali_info['weekday'],
                    'slots': [],
                    'available_count': 0
                }

            slots_by_date[date_key]['slots'].append(slot)
            if slot.is_available:
                slots_by_date[date_key]['available_count'] += 1

        return service_type, slots_by_date

    @staticmethod
    def lock_time_slot(slot_id):
        """
        Acquires a lock on the time slot, checks availability, and verifies against current time.
        Must be called within a transaction.
        Returns the locked TimeSlot object.
        """
        time_slot = TimeSlot.objects.select_for_update().get(
            id=slot_id,
            is_available=True,
            is_expired=False,
            deleted_at__isnull=True
        )

        tehran_tz = pytz.timezone('Asia/Tehran')
        now = timezone.now().astimezone(tehran_tz)
        slot_datetime = tehran_tz.localize(datetime.combine(time_slot.date, time_slot.start_time))

        if slot_datetime < now:
            raise ValueError('This time slot has expired due to passing time.')

        return time_slot

    @staticmethod
    def finalize_reservation(user, reservation_data, time_slot_id):
        """
        Creates the final Reservation object and marks the TimeSlot as unavailable.
        Must be called after successful OTP verification and within a transaction.
        Returns the created Reservation object.
        """
        with transaction.atomic():
            # Re-lock/re-check the slot within the final transaction
            time_slot = TimeSlot.objects.select_for_update().get(
                id=time_slot_id,
                is_available=True,
                is_expired=False
            )

            # Get consultation topic if provided
            consultation_topic = None
            topic_id = reservation_data.get('consultation_topic_id')
            if topic_id:
                consultation_topic = ConsultationTopic.objects.get(id=topic_id)

            # Create reservation
            reservation = Reservation.objects.create(
                user=user,
                service_type_id=reservation_data['service_type_id'],
                time_slot=time_slot,
                consultation_topic=consultation_topic,
                full_name=reservation_data['full_name'],
                phone_number=reservation_data['phone_number'],
                message=reservation_data.get('message', ''),
                status='phone_verified',
                payment_status='unpaid',
                phone_verified_at=timezone.now()
            )

            # Mark time slot as temporarily unavailable
            time_slot.is_available = False
            time_slot.save()

            return reservation

    @staticmethod
    def process_payment(reservation):
        """
        Handles the payment finalization and updates reservation status.
        (Currently implements fake payment as per the original code)
        """
        if reservation.status != 'phone_verified':
            raise ValueError("Reservation is not in the 'phone_verified' status.")

        with transaction.atomic():
            # 1. Create Payment record
            Payment.objects.create(
                reservation=reservation,
                amount=reservation.service_type.price,
                status='success',
                paid_at=timezone.now()
            )

            # 2. Update Reservation status
            reservation.status = 'paid'
            reservation.payment_status = 'paid'
            reservation.save()

        return reservation

    @staticmethod
    def get_review_info(tracking_code):
        """Retrieves reservation details and time-out info for the review step."""
        reservation = get_object_or_404(
            Reservation,
            tracking_code=tracking_code,
            deleted_at__isnull=True
        )

        if reservation.status == 'cancelled':
            raise ValueError('Reservation has expired.')

        jalali_info = get_jalali_date_info(reservation.time_slot.date)

        remaining_time = None
        if reservation.phone_verified_at:
            # 15 minutes lock window
            expires_at = reservation.phone_verified_at + timedelta(minutes=15)
            remaining_seconds = (expires_at - timezone.now()).total_seconds()
            if remaining_seconds > 0:
                remaining_time = int(remaining_seconds)

        return reservation, jalali_info, remaining_time
