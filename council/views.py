import secrets
from datetime import datetime, timedelta

import pytz
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_http_methods
from jdatetime import datetime as jdatetime

from accounts.models import OTP, User
from payments.models import Payment
from .forms import ReservationStepOneForm, OTPVerificationForm
from .models import Reservation, ServiceType, TimeSlot, ConsultationTopic
from .utils.reservation_expiration import release_expired_reservations, mark_expired_time_slots


class ReservationStep1View(View):
    """
    Step 1: Initial form - collect basic info and service type
    """
    template_name = 'council/step1_initial_form.html'

    def get(self, request):
        form = ReservationStepOneForm()
        service_types = ServiceType.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        ).order_by('order', 'name')

        consultation_topics = ConsultationTopic.objects.filter(
            is_active=True
        ).order_by('order', 'name')

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
            # Save basic reservation info in session
            request.session['reservation_data'] = {
                'full_name': form.cleaned_data['full_name'],
                'phone_number': form.cleaned_data['phone_number'],
                'service_type_id': form.cleaned_data['service_type'].id,
                'consultation_topic_id': form.cleaned_data.get('consultation_topic').id if form.cleaned_data.get(
                    'consultation_topic') else None,
                'message': form.cleaned_data.get('message', ''),
            }

            # Handle file upload separately
            if form.cleaned_data.get('prescription'):
                request.session['has_prescription'] = True

            messages.success(request, '✓ اطلاعات شما ثبت شد. لطفاً زمان مشاوره را انتخاب کنید.')
            return redirect('council:step2_select_time')

        service_types = ServiceType.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        ).order_by('order', 'name')

        consultation_topics = ConsultationTopic.objects.filter(
            is_active=True
        ).order_by('order', 'name')

        context = {
            'form': form,
            'service_types': service_types,
            'consultation_topics': consultation_topics,
            'step': 1
        }
        return render(request, self.template_name, context)


class ReservationStep2View(View):
    """
    Step 2: Select date and time slot
    Shows all slots but disables reserved/unavailable ones
    Filters out expired slots (past date/time)
    """
    template_name = 'council/step2_select_time.html'

    def get(self, request):
        # Check if step 1 is completed
        if 'reservation_data' not in request.session:
            messages.error(request, '⚠️ لطفاً ابتدا اطلاعات پایه را وارد کنید')
            return redirect('council:step1_initial')

        # Clean expired reservations and mark expired slots
        release_expired_reservations()
        mark_expired_time_slots()

        reservation_data = request.session['reservation_data']
        service_type = get_object_or_404(
            ServiceType,
            id=reservation_data['service_type_id'],
            is_active=True
        )

        # Get current datetime با timezone ایران
        tehran_tz = pytz.timezone('Asia/Tehran')
        now = timezone.now().astimezone(tehran_tz)
        today = now.date()
        current_time = now.time()
        end_date = today + timedelta(days=30)

        print(f"🕐 Tehran Time: {now}")
        print(f"📅 Today: {today}")
        print(f"⏰ Current Time: {current_time}")

        # Get time slots, excluding expired ones
        available_slots = TimeSlot.objects.filter(
            service_type=service_type,
            date__gte=today,
            date__lte=end_date,
            deleted_at__isnull=True,
            is_expired=False
        ).exclude(
            # Exclude slots that are today but time has passed
            date=today,
            start_time__lte=current_time
        ).select_related('service_type').order_by('date', 'start_time')

        # Group slots by date
        from jdatetime import datetime as jdatetime
        slots_by_date = {}
        for slot in available_slots:
            date_key = slot.date.strftime('%Y-%m-%d')
            if date_key not in slots_by_date:
                jalali = jdatetime.fromgregorian(date=slot.date)
                weekday_names = ['دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه', 'شنبه', 'یکشنبه']

                slots_by_date[date_key] = {
                    'date': slot.date,
                    'jalali_date': jalali,
                    'jalali_str': jalali.strftime('%Y/%m/%d'),
                    'weekday': weekday_names[jalali.weekday()],
                    'slots': [],
                    'available_count': 0
                }

            slots_by_date[date_key]['slots'].append(slot)
            if slot.is_available:
                slots_by_date[date_key]['available_count'] += 1

        context = {
            'service_type': service_type,
            'slots_by_date': slots_by_date,
            'reservation_data': reservation_data,
            'step': 2
        }
        return render(request, self.template_name, context)

    def post(self, request):
        # Get selected time slot
        slot_id = request.POST.get('time_slot_id')

        if not slot_id:
            messages.error(request, '⚠️ لطفاً یک زمان را انتخاب کنید')
            return redirect('council:step2_select_time')

        # Clean expired reservations and slots before locking
        release_expired_reservations()
        mark_expired_time_slots()

        try:
            with transaction.atomic():
                time_slot = TimeSlot.objects.select_for_update().get(
                    id=slot_id,
                    is_available=True,
                    is_expired=False,
                    deleted_at__isnull=True
                )

                # Double-check the slot hasn't passed
                now = datetime.now()
                slot_datetime = datetime.combine(time_slot.date, time_slot.start_time)

                if slot_datetime < now:
                    messages.error(request, '❌ این نوبت منقضی شده است')
                    return redirect('council:step2_select_time')

                # Save slot to session inside the transaction
                request.session['selected_time_slot_id'] = time_slot.id
                request.session.modified = True

        except TimeSlot.DoesNotExist:
            messages.error(request, '❌ این نوبت دیگر در دسترس نیست')
            return redirect('council:step2_select_time')

        messages.success(request, '✓ زمان مشاوره انتخاب شد. لطفاً شماره تلفن خود را تایید کنید.')
        return redirect('council:step3_verify_phone')


class ReservationStep3View(View):
    """
    Step 3: Phone verification with OTP
    """
    template_name = 'council/step3_verify_phone.html'

    def get(self, request):
        # Check if previous steps are completed
        if 'reservation_data' not in request.session or 'selected_time_slot_id' not in request.session:
            messages.error(request, '⚠️ لطفاً مراحل قبلی را تکمیل کنید')
            return redirect('council:step1_initial')

        reservation_data = request.session['reservation_data']
        time_slot = get_object_or_404(TimeSlot, id=request.session['selected_time_slot_id'])

        time_slot_jalali = jdatetime.fromgregorian(date=time_slot.date)
        weekday_names = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']
        time_slot_jalali_str = f"{weekday_names[time_slot_jalali.weekday()]} — {time_slot_jalali.strftime('%Y/%m/%d')}"

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
            return self.send_otp(request)
        elif action == 'verify_otp':
            return self.verify_otp(request)

        return redirect('council:step3_verify_phone')

    def send_otp(self, request):
        """Generate and send OTP code"""
        reservation_data = request.session.get('reservation_data')
        if not reservation_data:
            return JsonResponse({'success': False, 'message': 'اطلاعات رزرو یافت نشد'})

        phone_number = reservation_data['phone_number']

        # Generate OTP code
        otp_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])

        # Save OTP to database
        otp = OTP.objects.create(
            phone=phone_number,
            code=otp_code,
            expires_at=timezone.now() + timedelta(minutes=2)
        )

        # Print OTP in terminal (for development)
        print(f"\n{'=' * 50}")
        print(f"🔐 کد تایید OTP برای {phone_number}:")
        print(f"📱 کد: {otp_code}")
        print(f"⏰ انقضا: {otp.expires_at.strftime('%H:%M:%S')}")
        print(f"⏱️  زمان باقی‌مانده: 2 دقیقه")
        print(f"{'=' * 50}\n")

        # In production, send SMS here
        # send_sms(phone_number, f"کد تایید شما: {otp_code}")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'کد تایید برای شما ارسال شد',
                'expires_in': 120  # seconds
            })

        messages.success(request, '✓ کد تایید برای شما ارسال شد')
        return redirect('council:step3_verify_phone')

    def verify_otp(self, request):
        """Verify OTP code and create reservation"""
        form = OTPVerificationForm(request.POST)

        if not form.is_valid():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'کد وارد شده معتبر نیست'})
            messages.error(request, '❌ کد وارد شده معتبر نیست')
            return redirect('council:step3_verify_phone')

        otp_code = form.cleaned_data['otp_code']
        reservation_data = request.session.get('reservation_data')
        phone_number = reservation_data['phone_number']

        try:
            # Find valid OTP
            otp = OTP.objects.filter(
                phone=phone_number,
                code=otp_code,
                is_used=False,
                expires_at__gt=timezone.now()
            ).latest('created_at')
        except OTP.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'کد تایید نامعتبر یا منقضی شده است'})
            messages.error(request, '❌ کد تایید نامعتبر یا منقضی شده است')
            return redirect('council:step3_verify_phone')

        # Create or get user
        user, created = User.objects.get_or_create(
            phone=phone_number,
            defaults={
                'full_name': reservation_data['full_name'],
                'otp_verified': True
            }
        )

        if not created and not user.otp_verified:
            user.otp_verified = True
            user.save()

        # Mark OTP as used
        otp.mark_as_used(user=user)

        # Create reservation with atomic transaction
        try:
            with transaction.atomic():
                time_slot = TimeSlot.objects.select_for_update().get(
                    id=request.session['selected_time_slot_id'],
                    is_available=True,
                    is_expired=False
                )

                # Get consultation topic if provided
                consultation_topic = None
                if reservation_data.get('consultation_topic_id'):
                    consultation_topic = ConsultationTopic.objects.get(
                        id=reservation_data['consultation_topic_id']
                    )

                # Create reservation
                reservation = Reservation.objects.create(
                    user=user,
                    service_type_id=reservation_data['service_type_id'],
                    time_slot=time_slot,
                    consultation_topic=consultation_topic,
                    full_name=reservation_data['full_name'],
                    phone_number=phone_number,
                    message=reservation_data.get('message', ''),
                    status='phone_verified',
                    payment_status='unpaid',
                    phone_verified_at=timezone.now()
                )

                # Mark time slot as temporarily unavailable (will be released after 15 min if not paid)
                time_slot.is_available = False
                time_slot.save()

                # Store reservation info in session
                request.session['reservation_id'] = reservation.id
                request.session['reservation_tracking_code'] = reservation.tracking_code
                request.session['reservation_expires_at'] = (timezone.now() + timedelta(minutes=15)).isoformat()

                # Clear temporary data
                if 'reservation_data' in request.session:
                    del request.session['reservation_data']
                if 'selected_time_slot_id' in request.session:
                    del request.session['selected_time_slot_id']
                request.session.modified = True

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'رزرو شما با موفقیت ثبت شد',
                        'redirect_url': f"/council/review/{reservation.tracking_code}/"
                    })

                messages.success(request, '✓ شماره تلفن شما تایید شد')
                return redirect('council:step4_review', tracking_code=reservation.tracking_code)

        except TimeSlot.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'این نوبت دیگر در دسترس نیست'})
            messages.error(request, '❌ این نوبت دیگر در دسترس نیست')
            return redirect('council:step2_select_time')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': f'خطا در ثبت رزرو: {str(e)}'})
            messages.error(request, f'❌ خطا در ثبت رزرو: {str(e)}')
            return redirect('council:step3_verify_phone')


class ReservationStep4View(View):
    """
    Step 4: Review reservation and proceed to payment
    Checks for 15-minute timeout
    """
    template_name = 'council/step4_review.html'

    def get(self, request, tracking_code):

        # Clean expired reservations globally
        release_expired_reservations()

        reservation = get_object_or_404(
            Reservation,
            tracking_code=tracking_code,
            deleted_at__isnull=True
        )

        # If already cancelled by util → redirect user
        if reservation.status == 'cancelled':
            messages.error(request, '⏰ زمان رزرو شما به پایان رسیده است. لطفاً دوباره نوبت بگیرید.')
            return redirect('council:step1_initial')

        # Security check
        session_tracking = request.session.get('reservation_tracking_code')
        if session_tracking != tracking_code:
            if not request.user.is_authenticated or reservation.user != request.user:
                messages.error(request, '❌ شما دسترسی به این رزرو را ندارید')
                return redirect('council:step1_initial')

        # Convert date to Jalali
        jalali_date = jdatetime.fromgregorian(date=reservation.time_slot.date)
        weekday_names = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']
        jalali_date_str = f"{weekday_names[jalali_date.weekday()]} — {jalali_date.strftime('%Y/%m/%d')}"

        # Calculate remaining time to show on countdown timer
        remaining_time = None
        if reservation.phone_verified_at:
            expires_at = reservation.phone_verified_at + timedelta(minutes=15)
            remaining_seconds = (expires_at - timezone.now()).total_seconds()
            if remaining_seconds > 0:
                remaining_time = int(remaining_seconds)

        context = {
            'reservation': reservation,
            'jalali_date_str': jalali_date_str,
            'remaining_time': remaining_time,
            'step': 4
        }
        return render(request, self.template_name, context)

    def post(self, request, tracking_code):

        # Clean expired reservations globally
        release_expired_reservations()

        reservation = get_object_or_404(
            Reservation,
            tracking_code=tracking_code,
            status='phone_verified',
            deleted_at__isnull=True
        )

        # If expired during post (rare but possible)
        if reservation.status == 'cancelled':
            messages.error(request, '⏰ زمان رزرو شما به پایان رسیده است')
            return redirect('council:step1_initial')

        # Fake payment for now
        with transaction.atomic():
            payment = Payment.objects.create(
                reservation=reservation,
                amount=reservation.service_type.price,
                status='success',
                paid_at=timezone.now()
            )

            reservation.status = 'paid'
            reservation.payment_status = 'paid'
            reservation.save()

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

        jalali_date = jdatetime.fromgregorian(date=reservation.time_slot.date)

        context = {
            'reservation': reservation,
            'jalali_date': jalali_date,
            'payment': reservation.payments.filter(status='success').first()
        }
        return render(request, self.template_name, context)


# AJAX endpoint for checking slot availability
@require_http_methods(["GET"])
def check_slot_availability(request, slot_id):
    """Check if a time slot is still available and not expired"""
    try:
        slot = TimeSlot.objects.get(id=slot_id, deleted_at__isnull=True)

        tehran_tz = pytz.timezone('Asia/Tehran')
        now = timezone.now().astimezone(tehran_tz)
        slot_datetime = tehran_tz.localize(datetime.combine(slot.date, slot.start_time))

        is_expired = slot_datetime <= now

        return JsonResponse({
            'available': slot.is_available and not is_expired,
            'is_expired': is_expired,
            'date': str(slot.date),
            'start_time': slot.start_time.strftime('%H:%M'),
            'end_time': slot.end_time.strftime('%H:%M')
        })
    except TimeSlot.DoesNotExist:
        return JsonResponse({'available': False}, status=404)
