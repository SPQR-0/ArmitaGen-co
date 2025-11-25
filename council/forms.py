from django import forms

from .models import GeneticConsultationRequest


class GeneticConsultationRequestForm(forms.ModelForm):
    class Meta:
        model = GeneticConsultationRequest
        fields = ['full_name', 'phone_number', 'prescription_file', 'service_type', 'message']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام و نام خانوادگی'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره تلفن'
            }),
            'prescription_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png',
            }),
            'service_type': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'نوع خدمت درخواستی'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'پیام یا توضیحات تکمیلی'
            }),
        }

    def clean_service_type(self):
        val = self.cleaned_data.get('service_type')
        if val == '':
            raise forms.ValidationError("لطفاً یک خدمت معتبر انتخاب کنید.")
        return val