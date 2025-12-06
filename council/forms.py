from django import forms
from django.core.exceptions import ValidationError

from .models import Reservation, ServiceType, ConsultationTopic


class ReservationStepOneForm(forms.ModelForm):
    """
    Step 1: Initial reservation form
    Collects basic information and service type
    """

    class Meta:
        model = Reservation
        fields = ['full_name', 'phone_number', 'service_type', 'consultation_topic', 'message', 'prescription']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام و نام خانوادگی',
                'id': 'inputYourName'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control dz-number',
                'placeholder': 'شماره تلفن',
                'id': 'inputPhoneNumber',
                'dir': 'ltr'
            }),
            'service_type': forms.Select(attrs={
                'class': 'form-control bs-select',
                'data-style': 'form-control',
                'title': 'انتخاب نوع مشاوره',
                'id': 'inputServiceType'
            }),
            'consultation_topic': forms.Select(attrs={
                'class': 'form-control bs-select',
                'data-style': 'form-control',
                'title': 'انتخاب عنوان مشاوره (اختیاری)',
                'id': 'inputConsultationTopic'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'توضیحات و یادداشت‌های شما',
                'id': 'inputMessage'
            }),
            'prescription': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png',
                'id': 'inputPrescriptionFile'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter only active service types
        self.fields['service_type'].queryset = ServiceType.objects.filter(
            is_active=True,
            deleted_at__isnull=True
        ).order_by('order', 'name')

        # Filter only active consultation topics
        self.fields['consultation_topic'].queryset = ConsultationTopic.objects.filter(
            is_active=True
        ).order_by('order', 'name')

        # Make optional fields
        self.fields['prescription'].required = False
        self.fields['message'].required = False
        self.fields['consultation_topic'].required = False

    def clean_phone_number(self):
        """Validate Iranian phone number format"""
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Remove spaces and dashes
            phone = phone.replace(' ', '').replace('-', '')

            # Check if it starts with 09 or +989 or 989
            if not (phone.startswith('09') or phone.startswith('+989') or phone.startswith('989')):
                raise ValidationError('شماره تلفن باید با 09 شروع شود')

            # Normalize to 09XXXXXXXXX format
            if phone.startswith('+98'):
                phone = '0' + phone[3:]
            elif phone.startswith('98'):
                phone = '0' + phone[2:]

            # Check length
            if len(phone) != 11:
                raise ValidationError('شماره تلفن باید 11 رقم باشد')

            return phone
        return phone

    def clean_prescription(self):
        """Validate prescription file"""
        file = self.cleaned_data.get('prescription')
        if file:
            # Check file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError('حجم فایل نباید بیشتر از 5 مگابایت باشد')

            # Check file extension
            allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png']
            ext = file.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise ValidationError('فرمت فایل باید PDF، JPG یا PNG باشد')

        return file


class OTPVerificationForm(forms.Form):
    """
    OTP verification form
    """
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center otp-input',
            'placeholder': '--- ---',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
            'dir': 'ltr'
        }),
        label='کد تایید 6 رقمی'
    )

    def clean_otp_code(self):
        """Validate OTP code format"""
        code = self.cleaned_data.get('otp_code')
        if not code.isdigit():
            raise ValidationError('کد تایید باید فقط شامل اعداد باشد')
        return code
