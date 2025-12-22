from django import forms

from .models import Comment


class CommentForm(forms.ModelForm):
    """Form for submitting comments"""

    class Meta:
        model = Comment
        fields = ['name', 'email', 'content']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'comment-input',
                'placeholder': 'نام شما (اختیاری - برای ناشناس ماندن خالی بگذارید)',
                'maxlength': '100'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'comment-input',
                'placeholder': 'ایمیل شما (اختیاری)',
            }),
            'content': forms.Textarea(attrs={
                'class': 'comment-textarea',
                'placeholder': 'نظر خود را بنویسید...',
                'rows': '5',
                'required': 'required'
            }),
        }
        labels = {
            'name': '',
            'email': '',
            'content': '',
        }

    def clean_content(self):
        """Validate comment content"""
        content = self.cleaned_data.get('content')

        if not content or len(content.strip()) < 3:
            raise forms.ValidationError('نظر شما باید حداقل 3 کاراکتر باشد.')

        if len(content) > 2000:
            raise forms.ValidationError('نظر شما نباید بیشتر از 2000 کاراکتر باشد.')

        return content.strip()

    def clean_email(self):
        """Validate email if provided"""
        email = self.cleaned_data.get('email')

        if email:
            # Basic email validation is already done by EmailField
            return email.lower()

        return email


class ReplyForm(forms.ModelForm):
    """Form for replying to comments (similar to CommentForm but for clarity)"""

    class Meta:
        model = Comment
        fields = ['name', 'email', 'content']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'comment-input',
                'placeholder': 'نام شما (اختیاری)',
                'maxlength': '100'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'comment-input',
                'placeholder': 'ایمیل شما (اختیاری)',
            }),
            'content': forms.Textarea(attrs={
                'class': 'comment-textarea',
                'placeholder': 'پاسخ خود را بنویسید...',
                'rows': '4',
                'required': 'required'
            }),
        }
        labels = {
            'name': '',
            'email': '',
            'content': '',
        }

    def clean_content(self):
        """Validate reply content"""
        content = self.cleaned_data.get('content')

        if not content or len(content.strip()) < 3:
            raise forms.ValidationError('پاسخ شما باید حداقل 3 کاراکتر باشد.')

        if len(content) > 2000:
            raise forms.ValidationError('پاسخ شما نباید بیشتر از 2000 کاراکتر باشد.')

        return content.strip()

    def clean_email(self):
        """Validate email if provided"""
        email = self.cleaned_data.get('email')

        if email:
            return email.lower()

        return email
