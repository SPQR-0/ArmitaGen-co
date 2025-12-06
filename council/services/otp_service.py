import secrets
from datetime import timedelta

from django.utils import timezone

from accounts.models import OTP, User


class OTPService:
    """Handles OTP generation, sending, and verification."""

    @staticmethod
    def generate_and_send_otp(phone_number):
        """Generates, saves, and (simulates) sending an OTP code."""
        # Clean up any existing unused codes for this phone
        OTP.objects.filter(phone=phone_number, is_used=False).delete()

        otp_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        expires_at = timezone.now() + timedelta(minutes=2)

        otp = OTP.objects.create(
            phone=phone_number,
            code=otp_code,
            expires_at=expires_at
        )

        # In production, send SMS here (e.g., Kavenegar, Melipayamak)
        # send_sms(phone_number, f"کد تایید شما: {otp_code}")

        # Development print (as per original code)
        print(f"\n{'=' * 50}")
        print(f"🔐 کد تایید OTP برای {phone_number}:")
        print(f"📱 کد: {otp_code}")
        print(f"⏰ انقضا: {otp.expires_at.strftime('%H:%M:%S')}")
        print(f"⏱️  زمان باقی‌مانده: 2 دقیقه")
        print(f"{'=' * 50}\n")

        return otp

    @staticmethod
    def verify_otp_code(phone_number, otp_code):
        """Verifies the OTP code and returns the associated User object."""
        try:
            # Find the latest valid OTP
            otp = OTP.objects.filter(
                phone=phone_number,
                code=otp_code,
                is_used=False,
                expires_at__gt=timezone.now()
            ).latest('created_at')

            return otp

        except OTP.DoesNotExist:
            return None

    @staticmethod
    def create_or_update_user(phone_number, full_name):
        """Creates a new User or updates an existing one after successful OTP verification."""
        user, created = User.objects.get_or_create(
            phone=phone_number,
            defaults={
                'full_name': full_name,
                'otp_verified': True
            }
        )

        if not created and not user.otp_verified:
            user.otp_verified = True
            user.save()

        return user
