from django.shortcuts import render
from django.views import View



class CouncilView(View):
    temp = 'council/council.html'

    def get(self, request):
        return render(request, self.temp)
    
    def post(self, request):
        return render(request, self.temp)
    

# app_name/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import GeneticConsultationRequest

def genetic_consultation_view(request):
    if request.method == 'POST':
        try:
            # گرفتن داده‌ها از POST
            full_name = request.POST.get('full_name')
            phone_number = request.POST.get('phone_number')
            service_type = request.POST.get('service_type')
            message = request.POST.get('message')

            # گرفتن فایل آپلود شده از FILES
            prescription_file = request.FILES.get('prescription_file') 

            # ذخیره کردن در دیتابیس
            GeneticConsultationRequest.objects.create(
                full_name=full_name,
                phone_number=phone_number,
                service_type=service_type,
                message=message,
                prescription_file=prescription_file # ذخیره فایل
            )
            
            # ارسال پیام موفقیت آمیز
            messages.success(request, 'درخواست مشاوره شما با موفقیت ثبت شد. به زودی با شما تماس خواهیم گرفت.')
            
            # ریدایرکت به صفحه اصلی یا هر آدرس دیگر
            return redirect('home') # 'home' را با نام View/URL اصلی خود جایگزین کنید

        except Exception as e:
            messages.error(request, f'خطایی در ثبت درخواست رخ داد: {e}')
            # ریدایرکت برای جلوگیری از ارسال مجدد فرم
            return redirect(request.path_info)

    # اگر متد GET بود، فقط صفحه را نمایش بده
    return render(request, 'your_template_name.html', {})   