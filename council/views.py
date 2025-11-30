from django.contrib import messages
from django.shortcuts import render, redirect
from django.views import View



class CouncilView(View):
    template_name = 'council/council.html'

    def get(self, request):
    #     form = GeneticConsultationRequestForm()
    #     return render(request, self.template_name, {'form': form})
    #
    # def post(self, request):
    #     form = GeneticConsultationRequestForm(request.POST, request.FILES)
    #
    #     if form.is_valid():
    #         try:
    #             form.save()
    #             messages.success(request, 'درخواست مشاوره شما با موفقیت ثبت شد.')
    #             return redirect('council:con_success')
    #         except Exception as e:
    #             messages.error(request, f'خطا در ثبت درخواست: {str(e)}')
    #     else:
    #         messages.error(request, 'لطفاً اطلاعات فرم را به درستی تکمیل کنید.')

        return render(request, self.template_name)


class SuccessView(View):
    template_name = 'council/success.html'

    def get(self, request):
        return render(request, self.template_name)
