from django.shortcuts import render
from django.views import View


class AboutUsView(View):
    temp = 'team/about-us.html'

    def get(self, request):
        return render(request, self.temp)
    
    def post(self, request):
        return render(request, self.temp)
    

class ContactUsView(View):
    temp = 'team/contact-us.html'

    def get(self, request):
        return render(request, self.temp)
    
    def post(self, request):
        return render(request, self.temp)