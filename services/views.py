from django.shortcuts import render
from django.views import View


class IndexView(View):
    temp = 'home/index.html'

    def get(self, request):
        return render(request, self.temp)
    
    def post(self, request):
        return render(request, self.temp)
    

class TestView(View):
    temp = 'home/test.html'

    def get(self, request):
        return render(request, self.temp)
    
    def post(self, request):
        return render(request, self.temp)