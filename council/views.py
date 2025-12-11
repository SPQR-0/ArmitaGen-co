from datetime import datetime, timedelta

import pytz
from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_http_methods

from accounts.models import UserInfo
from logs.utils import log_activity, log_error
from .forms import OTPVerificationForm, ReservationStepOneForm
from .mixins import ExpiredSlotCleanupMixin, ReservationFlowMixin
from .models import Reservation, TimeSlot, ReservationSettings
from .services.otp_service import OTPService
from .services.reservation_service import ReservationService
from .utils.date_utils import get_jalali_date_info

def login_user_for_24h(request, user):
    """
    Log in the user and keep the session valid for 24 hours.
    """
    # Explicit backend is required since we are bypassing password authentication
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    # Set session expiry to 24 hours
    request.session.set_expiry(60 * 60 * 24)  # 24 hours


class ReservationStep1View(View):
    """
    Step 1: Initial form - collect basic info and service type
    """
    template_name = 'council/step1_initial_form.html'
    service = ReservationService()

    def get(self, request):

        form = ReservationStepOneForm()
        service_types, consultation_topics = self.service.get_step_one_data(request)

        # Log page view for guest
        log_activity(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key if not request.user.is_authenticated else None,
            action_type='page_view',
            description='مشاهده فرم اطلاعات اولیه رزرو',
            severity='info',
            request=request,
            metadata={
                'step': 1,
                'has_user': request.user.is_authenticated
            }
        )

        context = {
            'form': form,
            'service_types': service_types,
            'consultation_topics': consultation_topics,
            'step': 1
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = ReservationStepOneForm(request.POST, request.FILES)

        if form.is_valid():
            # Log form submission by guest
            log_activity(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key if not request.user.is_authenticated else None,
                action_type='reservation_start',
                description='ثبت اطلاعات اولیه رزرو توسط کاربر',
                severity='info',
                request=request,
                metadata={
                    'full_name': form.cleaned_data['full_name'],
                    'phone_number': form.cleaned_data['phone_number'],
                    'service_type': form.cleaned_data['service_type'].name,
                    'has_prescription': bool(form.cleaned_data.get('prescription')),
                    'step': 1
                }
            )

            # Store data in session
            request.session['reservation_data'] = {
                'full_name': form.cleaned_data['full_name'],
                'phone_number': form.cleaned_data['phone_number'],
                'service_type_id': form.cleaned_data['service_type'].id,
                'consultation_topic_id': form.cleaned_data.get('consultation_topic').id if form.cleaned_data.get(
                    'consultation_topic') else None,
                'message': form.cleaned_data.get('message', ''),
            }

            # Handle file upload separately (if applicable)
            if form.cleaned_data.get('prescription'):
                request.session['has_prescription'] = True

            messages.success(request, '✓ اطلاعات شما ثبت شد. لطفاً زمان مشاوره را انتخاب کنید.')
            return redirect('council:step2_select_time')

        # If form is invalid, re-render with context
        service_types, consultation_topics = self.service.get_step_one_data(request)
        context = {
            'form': form,
            'service_types': service_types,
            'consultation_topics': consultation_topics,
            'step': 1
        }
        return render(request, self.template_name, context)


class ReservationStep2View(ExpiredSlotCleanupMixin, ReservationFlowMixin, View):
    """
    Step 2: Select date and time slot
    """
    template_name = 'council/step2_select_time.html'
    service = ReservationService()

    def get(self, request):
        check = self.check_step_one_completed(request)
        if check:
            return check

        # Log time selection page view
        log_activity(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key if not request.user.is_authenticated else None,
            action_type='page_view',
            description='مشاهده صفحه انتخاب زمان',
            severity='info',
            request=request,
            metadata={
                'step': 2,
                'service_type_id': request.session['reservation_data']['service_type_id']
            }
        )

        reservation_data = request.session['reservation_data']
        service_type, slots_by_date = self.service.get_available_time_slots(
            reservation_data['service_type_id']
        )

        context = {
            'service_type': service_type,
            'slots_by_date': slots_by_date,
            'reservation_data': reservation_data,
            'step': 2
        }
        return render(request, self.template_name, context)

    def post(self, request):
        slot_id = request.POST.get('time_slot_id')

        if not slot_id:
            messages.error(request, '⚠️ لطفاً یک زمان را انتخاب کنید')
            return redirect('council:step2_select_time')

        try:
            # Lock slot using the Service layer logic inside a transaction
            with transaction.atomic():
                time_slot = self.service.lock_time_slot(slot_id)
                # Save slot to session inside the transaction lock
                request.session['selected_time_slot_id'] = time_slot.id
                request.session.modified = True

                # Log slot selection by guest
                log_activity(
                    user=request.user if request.user.is_authenticated else None,
                    session_key=request.session.session_key if not request.user.is_authenticated else None,
                    action_type='reservation_start',
                    description='انتخاب زمان مشاوره',
                    severity='info',
                    request=request,
                    metadata={
                        'slot_id': time_slot.id,
                        'slot_date': str(time_slot.date),
                        'slot_time': f"{time_slot.start_time} - {time_slot.end_time}",
                        'step': 2
                    }
                )

        except TimeSlot.DoesNotExist:
            messages.error(request, '❌ این نوبت دیگر در دسترس نیست')
            return redirect('council:step2_select_time')
        except ValueError as e:
            messages.error(request, f'❌ {str(e)}')
            return redirect('council:step2_select_time')

        messages.success(request, '✓ زمان مشاوره انتخاب شد. لطفاً شماره تلفن خود را تایید کنید.')
        return redirect('council:step3_verify_phone')


class ReservationStep3View(ReservationFlowMixin, View):
    """
    Step 3: Phone verification with OTP
    """
    template_name = 'council/step3_verify_phone.html'
    otp_service = OTPService()
    res_service = ReservationService()

    def get(self, request):
        # Use Mixin to check flow
        check = self.check_step_one_completed(request) or self.check_step_two_completed(request)
        if check:
            return check

        reservation_data = request.session['reservation_data']
        time_slot = get_object_or_404(TimeSlot, id=request.session['selected_time_slot_id'])

        jalali_info = get_jalali_date_info(time_slot.date)
        time_slot_jalali_str = f"{jalali_info['weekday']} — {jalali_info['jalali_str']}"

        form = OTPVerificationForm()

        context = {
            'form': form,
            'reservation_data': reservation_data,
            'time_slot': time_slot,
            'time_slot_jalali_str': time_slot_jalali_str,
            'step': 3
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get('action')

        if action == 'send_otp':
            return self._send_otp_handler(request)
        elif action == 'verify_otp':
            return self._verify_otp_handler(request)

        return redirect('council:step3_verify_phone')

    def _send_otp_handler(self, request):
        """Handler for sending OTP code (delegated to service)"""
        reservation_data = request.session.get('reservation_data')
        if not reservation_data:
            return JsonResponse({'success': False, 'message': 'اطلاعات رزرو یافت نشد'})

        phone_number = reservation_data['phone_number']
        self.otp_service.generate_and_send_otp(phone_number)  # Call Service layer

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'کد تایید برای شما ارسال شد',
                'expires_in': 120  # seconds
            })

        messages.success(request, '✓ کد تایید برای شما ارسال شد')
        return redirect('council:step3_verify_phone')

    # Step 2: Save reservation data into session
    def step2_submit_reservation(self, request):
        if request.method == "POST":
            full_name = request.POST.get("full_name")
            phone_number = request.POST.get("phone_number")
            time_slot_id = request.POST.get("time_slot_id")

            if not full_name or not phone_number or not time_slot_id:
                messages.error(request, '❌ لطفا همه فیلدها را پر کنید')
                return redirect('council:step2_select_time')

            # Save in session
            request.session['reservation_data'] = {
                'full_name': full_name,
                'phone_number': phone_number
            }
            request.session['selected_time_slot_id'] = time_slot_id
            request.session.modified = True

            return redirect('council:step3_verify_phone')

    def _verify_otp_handler(self, request):
        """Handler for verifying OTP code and creating reservation"""
        reservation_data = request.session.get('reservation_data')
        time_slot_id = request.session.get('selected_time_slot_id')

        # Safety check: redirect if session data missing
        if not reservation_data or not time_slot_id:
            msg = 'لطفا ابتدا فرم رزرو را تکمیل کنید'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': msg})
            messages.error(request, f'❌ {msg}')
            return redirect('council:step1_start_reservation')

        form = OTPVerificationForm(request.POST)
        if not form.is_valid():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'کد وارد شده معتبر نیست'})
            messages.error(request, '❌ کد وارد شده معتبر نیست')
            return redirect('council:step3_verify_phone')

        otp_code = form.cleaned_data['otp_code']
        phone_number = reservation_data['phone_number']
        guest_session_key = request.session.session_key

        otp = self.otp_service.verify_otp_code(phone_number, otp_code)
        if not otp:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'کد تایید نامعتبر یا منقضی شده است'})
            messages.error(request, '❌ کد تایید نامعتبر یا منقضی شده است')
            return redirect('council:step3_verify_phone')

        try:
            # Create or update user (update full_name if changed)
            user = self.otp_service.create_or_update_user(
                phone_number,
                reservation_data['full_name']
            )

            # Mark OTP as used
            otp.mark_as_used(user=user)

            # Log user in
            login_user_for_24h(request, user)

            try:
                UserInfo.create_or_update_for_user(user)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to update UserInfo for user {user.id}: {e}")

            # Finalize reservation
            reservation = self.res_service.finalize_reservation(
                user,
                reservation_data,
                time_slot_id
            )

            # Log activity
            log_activity(
                user=user,
                action_type='otp_verify',
                description=f'تایید موفق کد OTP و ایجاد رزرو {reservation.tracking_code}',
                severity='info',
                request=request,
                metadata={
                    'reservation_id': reservation.id,
                    'tracking_code': reservation.tracking_code,
                    'migrated_from_session': guest_session_key,
                    'step': 3
                }
            )

            # Safely remove session keys
            request.session.pop('reservation_data', None)
            request.session.pop('selected_time_slot_id', None)
            request.session['reservation_id'] = reservation.id
            request.session['reservation_tracking_code'] = reservation.tracking_code
            request.session.modified = True

            # Return JSON for AJAX or redirect
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'رزرو شما با موفقیت ثبت شد',
                    'redirect_url': f"/council/review/{reservation.tracking_code}/"
                })

            messages.success(request, '✓ شماره تلفن شما تایید شد')
            return redirect('council:step4_review', tracking_code=reservation.tracking_code)

        except TimeSlot.DoesNotExist:
            msg = 'این نوبت دیگر در دسترس نیست'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': msg})
            messages.error(request, f'❌ {msg}')
            return redirect('council:step2_select_time')


        except Exception as e:
            log_error(
                error_type='reservation',
                error_message=str(e),
                user=request.user if request.user.is_authenticated else None,
                request=request,
                view_name='ReservationStep3View'
            )
            msg = f'خطا در ثبت رزرو: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': msg})
            messages.error(request, f'❌ {msg}')
            return redirect('council:step3_verify_phone')


class ReservationStep4View(ExpiredSlotCleanupMixin, View):
    """
    Step 4: Review reservation and proceed to payment
    Checks for 15-minute timeout
    """
    template_name = 'council/step4_review.html'
    service = ReservationService()

    def get(self, request, tracking_code):
        try:
            # Get data from Service layer
            reservation, jalali_info, remaining_time = self.service.get_review_info(tracking_code)

        except ValueError:
            messages.error(request, '⏰ زمان رزرو شما به پایان رسیده است. لطفاً دوباره نوبت بگیرید.')
            return redirect('council:step1_initial')
        except Reservation.DoesNotExist:
            messages.error(request, '❌ رزرو مورد نظر یافت نشد.')
            return redirect('council:step1_initial')

        # Security check (can be improved with a dedicated decorator/middleware)
        session_tracking = request.session.get('reservation_tracking_code')
        if session_tracking != tracking_code:
            if not request.user.is_authenticated or reservation.user != request.user:
                messages.error(request, '❌ شما دسترسی به این رزرو را ندارید')
                return redirect('council:step1_initial')

        jalali_date_str = f"{jalali_info['weekday']} — {jalali_info['jalali_str']}"

        context = {
            'reservation': reservation,
            'jalali_date_str': jalali_date_str,
            'remaining_time': remaining_time,
            'step': 4
        }
        return render(request, self.template_name, context)

    def post(self, request, tracking_code):
        reservation = get_object_or_404(
            Reservation,
            tracking_code=tracking_code,
            status='phone_verified',
            deleted_at__isnull=True
        )

        try:
            # Process payment via Service layer
            reservation = self.service.process_payment(reservation)

            # UPDATE UserInfo after successful payment
            if reservation.user:
                try:
                    UserInfo.create_or_update_for_user(reservation.user)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to update UserInfo after payment: {e}")


        except ValueError as e:
            messages.error(request, f'❌ {str(e)}')
            return redirect('council:step4_review', tracking_code=tracking_code)
        except Exception as e:
            messages.error(request, f'❌ خطا در فرآیند پرداخت: {str(e)}')
            return redirect('council:step4_review', tracking_code=tracking_code)

        messages.success(request, '✓ پرداخت با موفقیت انجام شد')
        return redirect('council:final_receipt', tracking_code=reservation.tracking_code)


class ReservationReceiptView(View):
    """
    Final step: Display reservation receipt/ticket
    """
    template_name = 'council/receipt.html'

    def get(self, request, tracking_code):
        reservation = get_object_or_404(
            Reservation,
            tracking_code=tracking_code,
            deleted_at__isnull=True
        )

        jalali_info = get_jalali_date_info(reservation.time_slot.date)

        context = {
            'reservation': reservation,
            'jalali_date': jalali_info['jalali_date'],
            'payment': reservation.payments.filter(status='success').first()
        }
        return render(request, self.template_name, context)


# AJAX endpoint (Remains largely the same, but uses a simplified logic for time check)
@require_http_methods(["GET"])
def check_slot_availability(request, slot_id):
    """Check if a time slot is available and fits the 24h rule"""
    try:
        slot = TimeSlot.objects.get(id=slot_id, deleted_at__isnull=True)

        tehran_tz = pytz.timezone('Asia/Tehran')
        now = timezone.now().astimezone(tehran_tz)
        slot_datetime = tehran_tz.localize(datetime.combine(slot.date, slot.start_time))
        settings_obj = ReservationSettings.active()
        expiration_deadline = slot_datetime - timedelta(days=settings_obj.expiration_slot_day)

        is_expired = now >= expiration_deadline

        # is_expired = (now + timedelta(days=1)) >= slot_datetime

        return JsonResponse({
            'available': slot.is_available and not is_expired and not slot.is_expired,
            'is_expired': is_expired or slot.is_expired,
            'date': str(slot.date),
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': slot.end_time.strftime('%H:%M')
        })
    except TimeSlot.DoesNotExist:
        return JsonResponse({'available': False}, status=404)


def get_service_slots_api(request, service_type_id):
    """
    API endpoint to fetch fresh slots data in JSON format for AJAX updates.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        service_type, slots_by_date = ReservationService.get_available_time_slots(service_type_id)

        json_data = {}
        for date_key, data in slots_by_date.items():
            json_data[date_key] = {
                'available_count': data['available_count'],
                'slots': [
                    {
                        'id': slot.id,
                        'start_time': slot.start_time.strftime('%H:%M'),
                        'end_time': slot.end_time.strftime('%H:%M'),
                        'is_available': slot.is_available
                    } for slot in data['slots']
                ]
            }

        return JsonResponse({'status': 'success', 'data': json_data})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
