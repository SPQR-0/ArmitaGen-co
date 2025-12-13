from django.conf import settings
from kavenegar import KavenegarAPI, APIException, HTTPException

from accounts.models import OTP, User, UserInfo


class OTPService:
    """
    OTP Management Service.
    Integrated with User, OTP, and UserInfo models.
    """

    @staticmethod
    def generate_and_send_otp(phone_number):
        """
        Creates a new OTP and sends SMS.
        """
        # 1. Clean up unused previous codes
        OTP.objects.filter(phone=phone_number, is_used=False).delete()

        # 2. Create OTP object (Model handles code generation)
        otp = OTP.objects.create(phone=phone_number)

        # 3. Terminal Log
        print(f"\n{'=' * 50}")
        print(f"OTP Code for {phone_number}:")
        print(f"Code: {otp.code}")
        print(f"Expires at: {otp.expires_at.strftime('%H:%M:%S')}")
        print(f"{'=' * 50}\n")

        # 4. Send SMS via Kavenegar
        OTPService._send_kavenegar_sms(phone_number, otp.code)

        return otp

    @staticmethod
    def _send_kavenegar_sms(phone_number, code):
        """Internal helper method to handle Kavenegar API calls."""
        try:
            api_key = getattr(settings, 'KAVENEGAR_API_KEY', None)
            sender = getattr(settings, 'KAVENEGAR_SENDER', None)

            if not api_key:
                print("Error: KAVENEGAR_API_KEY is not set.")
                return False

            api = KavenegarAPI(api_key)

            # Message content in Persian
            message = (
                f"کد ورود: {code}\n"
                f"این کد تا ۲ دقیقه معتبر است."
            )

            params = {
                'sender': sender,
                'receptor': phone_number,
                'message': message
            }

            response = api.sms_send(params)

            if response and isinstance(response, list) and response[0]['status'] == 1:
                print(f"SMS sent successfully to {phone_number}")
                return True
            return False

        except (APIException, HTTPException, Exception) as e:
            # Print specific error but don't crash
            print(f"SMS Sending Error: {e}")
            return False

    @staticmethod
    def verify_otp_code(phone_number, otp_code):
        """Verifies the OTP code and returns the valid OTP object."""
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
        """
        Creates or updates the user after successful OTP verification.
        Restored original method name for compatibility.
        """

        # 1. Get or Create User
        user, created = User.objects.get_or_create(
            phone=phone_number,
            defaults={
                'full_name': full_name,
                'otp_verified': True,
                'is_active': True
            }
        )

        # Update existing user if needed
        if not created and not user.otp_verified:
            user.otp_verified = True
            user.save()

        # 2. Burn OTP code (if instance is provided)
        if otp_instance:
            otp_instance.mark_as_used(user=user)

        # 3. Create or Update UserInfo
        UserInfo.create_or_update_for_user(user)

        # Return just user (to match your original code signature)
        return user
