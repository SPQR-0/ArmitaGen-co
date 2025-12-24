from datetime import datetime, timedelta

import pytz
from django.contrib import messages
from django.contrib.auth import login
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views import View
from django.views.decorators.http import require_http_methods

from accounts.models import User
from logs.utils import log_activity
from payments.models import Payment
from .forms import ReservationStepOneForm
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
    Step 1: Initial form - collect basic info and service type (WITHOUT phone number)
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
                    # phone_number removed from here
                    'service_type': form.cleaned_data['service_type'].name,
                    'has_prescription': bool(form.cleaned_data.get('prescription')),
                    'step': 1
                }
            )

            # Handle prescription file FIRST before storing other data
            prescription_path = None
            prescription_file = form.cleaned_data.get('prescription')

            if prescription_file:
                # Save file immediately to disk
                from django.core.files.storage import default_storage
                from datetime import datetime

                # Create directory structure
                now = datetime.now()
                year = now.strftime("%Y")
                month = now.strftime("%m")
                user_name = slugify(form.cleaned_data['full_name'], allow_unicode=True)

                # Get file extension
                ext = prescription_file.name.split('.')[-1] if '.' in prescription_file.name else 'jpg'
                filename = f"prescription.{ext}"

                # Build path
                relative_path = f"prescriptions/{year}/{month}/{user_name}/{filename}"
                print(now, year, month, user_name, relative_path)

                # Save file
                prescription_path = default_storage.save(relative_path, prescription_file)

            # Store data in session (WITHOUT phone_number)
            request.session['reservation_data'] = {
                'full_name': form.cleaned_data['full_name'],
                # phone_number removed from here - will be added in step 2
                'service_type_id': form.cleaned_data['service_type'].id,
                'consultation_topic_id': form.cleaned_data.get('consultation_topic').id if form.cleaned_data.get(
                    'consultation_topic') else None,
                'message': form.cleaned_data.get('message', ''),
                'prescription_path': prescription_path,
            }

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
    Step 2: Unified view for Slot Selection, OTP Verification, and Invoice Review.
    Phone number is collected HERE when user requests OTP.
    """
    template_name = 'council/step2_select_time.html'
    service = ReservationService()

    def get(self, request):
        # بررسی اینکه آیا مرحله اول (اطلاعات اولیه) تکمیل شده است
        check = self.check_step_one_completed(request)
        if check:
            return check

        reservation_data = request.session.get('reservation_data')
        service_type, slots_by_date = self.service.get_available_time_slots(
            reservation_data['service_type_id']
        )

        # لاگ مشاهده صفحه
        log_activity(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key if not request.user.is_authenticated else None,
            action_type='page_view',
            description='مشاهده صفحه انتخاب زمان و تایید هویت',
            severity='info',
            request=request,
            metadata={'step': 2, 'service_id': reservation_data['service_type_id']}
        )

        context = {
            'service_type': service_type,
            'slots_by_date': slots_by_date,
            'reservation_data': reservation_data,
            'step': 2
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get('action')

        # ۱. اکشن انتخاب اسلات (Select Slot)
        if action == 'select_slot':
            return self._handle_select_slot(request)

        # ۲. اکشن ارسال کد تایید (Send OTP) - NOW with phone number collection
        elif action == 'send_otp':
            return self._handle_send_otp(request)

        # ۳. اکشن بررسی کد تایید (Verify OTP)
        elif action == 'verify_otp':
            return self._handle_verify_otp(request)

        # ۴. اکشن جدید: نهایی سازی و رفتن به درگاه
        elif action == 'finalize_booking':
            return self._handle_finalize_booking(request)

        return JsonResponse({'success': False, 'message': 'درخواست نامعتبر است.'})

    def _handle_select_slot(self, request):
        slot_id = request.POST.get('time_slot_id')
        if not slot_id:
            return JsonResponse({'success': False, 'message': 'لطفاً یک زمان را انتخاب کنید.'})

        try:
            with transaction.atomic():
                time_slot = self.service.lock_time_slot(slot_id)
                request.session['selected_time_slot_id'] = time_slot.id
                request.session.modified = True

                log_activity(
                    user=request.user if request.user.is_authenticated else None,
                    action_type='reservation_start',
                    description=f'انتخاب زمان: {time_slot.start_time}',
                    request=request,
                    metadata={'slot_id': slot_id}
                )
                return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    def _handle_send_otp(self, request):
        """
        UPDATED: Now collects phone number from POST data and saves it to session
        """
        phone_number = request.POST.get('phone_number')

        # اعتبارسنجی شماره تلفن
        if not phone_number:
            return JsonResponse({'success': False, 'message': 'شماره تلفن الزامی است.'})

        # اعتبارسنجی فرمت شماره (اختیاری - می‌توانید پیچیده‌تر کنید)
        if not phone_number.startswith('09') or len(phone_number) != 11:
            return JsonResponse({'success': False, 'message': 'لطفاً شماره موبایل معتبر وارد کنید (مثال: 09123456789)'})

        try:
            # ارسال کد OTP
            otp_instance = OTPService.generate_and_send_otp(phone_number)

            if otp_instance:
                # ذخیره شماره تلفن در session برای استفاده در مرحله بعد
                request.session['temp_phone_number'] = phone_number

                # همچنین شماره را به reservation_data اضافه کنید
                res_data = request.session.get('reservation_data', {})
                res_data['phone_number'] = phone_number
                request.session['reservation_data'] = res_data

                request.session.modified = True

                # لاگ ارسال OTP
                log_activity(
                    user=request.user if request.user.is_authenticated else None,
                    session_key=request.session.session_key if not request.user.is_authenticated else None,
                    action_type='otp_sent',
                    description=f'ارسال کد تایید به شماره {phone_number}',
                    severity='info',
                    request=request,
                    metadata={'phone_number': phone_number, 'step': 2}
                )

                return JsonResponse({
                    'success': True,
                    'message': 'کد تایید با موفقیت ارسال شد.'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'خطا در ارسال پیامک. لطفاً مجدداً تلاش کنید.'
                })

        except Exception as e:
            print(f"Error in sending OTP: {e}")
            return JsonResponse({
                'success': False,
                'message': 'خطای سیستمی رخ داده است.'
            })

    def _handle_verify_otp(self, request):
        """
        UPDATED: Uses phone number from session (saved in _handle_send_otp)
        """
        otp_code = request.POST.get('otp_code')
        phone_number = request.session.get('temp_phone_number')

        # بررسی اینکه شماره تلفن در سشن موجود است
        if not phone_number:
            return JsonResponse({'success': False, 'message': 'ابتدا شماره تلفن خود را وارد کرده و کد را دریافت کنید.'})

        # واکشی اطلاعات مرحله اول (نام متقاضی) از سشن
        res_data = request.session.get('reservation_data', {})
        applicant_name = res_data.get('full_name', 'مهمان')

        # بررسی واقعی کد تایید با استفاده از سرویس OTPService
        from .services.otp_service import OTPService
        otp_instance = OTPService.verify_otp_code(phone_number, otp_code)

        if otp_instance:
            # تایید موفق: ایجاد یا بروزرسانی کاربر در دیتابیس
            user = OTPService.create_or_update_user(
                phone_number=phone_number,
                full_name=applicant_name,
                otp_instance=otp_instance
            )

            # بروزرسانی اطلاعات سشن با شماره تلفن تایید شده
            res_data['phone_number'] = phone_number
            request.session['reservation_data'] = res_data
            request.session['step_two_completed'] = True
            request.session.modified = True

            # لاگ تایید موفق
            log_activity(
                user=user,
                action_type='otp_verified',
                description=f'تایید موفق کد OTP برای شماره {phone_number}',
                severity='info',
                request=request,
                metadata={'phone_number': phone_number, 'user_id': user.id, 'step': 2}
            )

            # واکشی اطلاعات اسلات و قیمت داینامیک
            slot_id = request.session.get('selected_time_slot_id')
            try:
                time_slot = TimeSlot.objects.select_related('service_type').get(id=slot_id)
                formatted_price = "{:,}".format(time_slot.service_type.price)

                # ارسال دیتای نهایی به فرانت‌اِند برای گام Review
                return JsonResponse({
                    'success': True,
                    'message': 'هویت تایید شد',
                    'review_data': {
                        'full_name': applicant_name,
                        'phone': phone_number,
                        'service_name': time_slot.service_type.name,
                        'date': str(time_slot.date),
                        'time': f"{time_slot.start_time.strftime('%H:%M')} تا {time_slot.end_time.strftime('%H:%M')}",
                        'price': formatted_price
                    }
                })
            except (TimeSlot.DoesNotExist, AttributeError):
                return JsonResponse({'success': False, 'message': 'اطلاعات نوبت یا سرویس یافت نشد.'})

        else:
            # اگر کد اشتباه یا منقضی بود
            log_activity(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key,
                action_type='otp_failed',
                description=f'کد OTP اشتباه برای شماره {phone_number}',
                severity='warning',
                request=request,
                metadata={'phone_number': phone_number, 'step': 2}
            )
            return JsonResponse({'success': False, 'message': 'کد وارد شده اشتباه است یا منقضی شده است.'})

    def _handle_finalize_booking(self, request):
        """
        UPDATED: Now properly handles phone number from session
        """
        # بررسی اینکه کاربر مرحله قبل (OTP) را رد کرده باشد
        if not request.session.get('step_two_completed'):
            return JsonResponse({'success': False, 'message': 'لطفاً ابتدا مراحل تایید هویت را تکمیل کنید.'})

        try:
            with transaction.atomic():
                # دریافت اطلاعات از سشن
                res_data = request.session.get('reservation_data')
                slot_id = request.session.get('selected_time_slot_id')

                # شماره تلفن حالا در reservation_data ذخیره شده است
                phone_number = res_data.get('phone_number')

                if not phone_number:
                    # fallback به temp_phone_number اگر به هر دلیلی در reservation_data نبود
                    phone_number = request.session.get('temp_phone_number')

                if not phone_number:
                    return JsonResponse({'success': False, 'message': 'شماره تلفن یافت نشد. لطفاً مجدداً امتحان کنید.'})

                # پیدا کردن کاربر با شماره تلفن
                try:
                    user = User.objects.get(phone=phone_number)
                except User.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'کاربر یافت نشد. لطفاً مجدداً وارد شوید.'})

                # ساخت رزرو واقعی
                reservation = self.service.finalize_reservation(
                    user=user,
                    reservation_data=res_data,
                    time_slot_id=slot_id
                )

                # === ایجاد پرداخت موفق ساختگی (Bypass) ===
                fake_payment = Payment.objects.create(
                    reservation=reservation,
                    amount=reservation.service_type.price,
                    status='success',
                )

                # تغییر وضعیت رزرو
                reservation.payment_status = 'paid'
                reservation.status = 'phone_verified'
                reservation.save()

                # لاگ نهایی‌سازی رزرو
                log_activity(
                    user=user,
                    action_type='reservation_completed',
                    description=f'رزرو با کد پیگیری {reservation.tracking_code} تکمیل شد',
                    severity='info',
                    request=request,
                    metadata={
                        'reservation_id': reservation.id,
                        'tracking_code': reservation.tracking_code,
                        'phone_number': phone_number
                    }
                )

                # پاکسازی سشن
                keys_to_remove = ['reservation_data', 'selected_time_slot_id', 'temp_phone_number',
                                  'step_two_completed']
                for key in keys_to_remove:
                    if key in request.session:
                        del request.session[key]
                request.session.modified = True

                # ساخت لینک رسید
                receipt_url = reverse('council:final_receipt', kwargs={'tracking_code': reservation.tracking_code})

                return JsonResponse({
                    'success': True,
                    'payment_url': receipt_url
                })

        except Exception as e:
            print(f"Finalize Error: {e}")
            log_activity(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key,
                action_type='reservation_error',
                description=f'خطا در نهایی‌سازی رزرو: {str(e)}',
                severity='error',
                request=request,
                metadata={'error': str(e)}
            )
            return JsonResponse({'success': False, 'message': f'خطا در ثبت نهایی: {str(e)}'})


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


# Main Council Information Page
class InfoView(View):
    temp = 'council/info.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)
