from django.conf import settings
from kavenegar import KavenegarAPI, APIException, HTTPException
from accounts.models import OTP, User, UserInfo

class OTPService:
    @staticmethod
    def generate_and_send_otp(phone_number):
        """تولید کد و ارسال از طریق متد Lookup"""
        # ۱. پاکسازی کدهای قبلی
        OTP.objects.filter(phone=phone_number, is_used=False).delete()

        # ۲. ایجاد شیء OTP
        otp = OTP.objects.create(phone=phone_number)

        # ۳. لاگ در ترمینال برای دیباگ
        print(f"\n{'=' * 50}")
        print(f"OTP for {phone_number}: {otp.code}")
        print(f"{'=' * 50}\n")

        # ۴. ارسال از طریق کاوه نگار (Lookup)
        OTPService._send_kavenegar_lookup(phone_number, otp.code)

        return otp

    @staticmethod
    def _send_kavenegar_lookup(phone_number, code):
        """ارسال پیامک با استفاده از متد Verify Lookup (عبور از بلک‌لیست)"""
        try:
            api_key = getattr(settings, 'KAVENEGAR_API_KEY', None)
            if not api_key:
                print("Error: KAVENEGAR_API_KEY is not set.")
                return False

            api = KavenegarAPI(api_key)

            # پارامترها برای متد Lookup
            # template: نام الگویی که در پنل کاوه نگار تعریف کرده‌اید
            # token: مقداری که جایگزین %token% در الگو می‌شود
            params = {
                'receptor': phone_number,
                'template': 'verify',  # نام الگوی خود را اینجا بنویسید
                'token': code,
            }

            response = api.verify_lookup(params)
            
            if response:
                print(f"Lookup SMS sent successfully to {phone_number}")
                return True
            return False

        except (APIException, HTTPException, Exception) as e:
            print(f"Kavenegar Lookup Error: {e}")
            return False

    # سایر متدها (verify_otp_code و create_or_update_user) بدون تغییر باقی می‌مانند
    @staticmethod
    def verify_otp_code(phone_number, otp_code):
        try:
            otp = OTP.objects.filter(
                phone=phone_number,
                code=otp_code,
                is_used=False
            ).latest('created_at')

            if otp.is_expired():
                return None
            return otp
        except OTP.DoesNotExist:
            return None

    @staticmethod
    def create_or_update_user(phone_number, full_name, otp_instance=None):
        user, created = User.objects.get_or_create(
            phone=phone_number,
            defaults={
                'full_name': full_name,
                'otp_verified': True,
                'is_active': True
            }
        )
        if not created and not user.otp_verified:
            user.otp_verified = True
            user.save()

        if otp_instance:
            otp_instance.mark_as_used(user=user)

        UserInfo.create_or_update_for_user(user)
        return user