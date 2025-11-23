from django import forms

from .models import GeneticConsultationRequest


class GeneticConsultationRequestForm(forms.ModelForm):
    class Meta:
        model = GeneticConsultationRequest
        fields = ['full_name', 'phone_number', 'prescription_file', 'service_type', 'message']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام و نام خانوادگی'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره تلفن'}),
            'service_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نوع خدمت درخواستی'}),
            'message': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'پیام یا توضیحات تکمیلی'}),
        }
