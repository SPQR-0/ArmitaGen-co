from django.contrib import messages
from django.shortcuts import redirect

from .utils.reservation_expiration import (mark_expired_time_slots,
                                           release_expired_reservations)


class ReservationFlowMixin:
    """
    Mixin for checking if previous steps are completed and redirecting if necessary.
    """

    def check_step_one_completed(self, request):
        if 'reservation_data' not in request.session:
            messages.error(request, '⚠️ لطفاً ابتدا اطلاعات پایه را وارد کنید')
            return redirect('council:step1_initial')
        return None  # Return None if check passes

    def check_step_two_completed(self, request):
        if 'selected_time_slot_id' not in request.session:
            messages.error(request, '⚠️ لطفاً زمان مشاوره را انتخاب کنید')
            return redirect('council:step2_select_time')
        return None


class ExpiredSlotCleanupMixin:
    """
    Mixin to ensure expired reservations and slots are cleaned up before critical operations.
    """

    def dispatch(self, request, *args, **kwargs):
        # Clean expired reservations and mark expired slots before any View logic runs
        release_expired_reservations()
        mark_expired_time_slots()
        return super().dispatch(request, *args, **kwargs)
