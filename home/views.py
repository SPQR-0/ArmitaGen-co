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


class BrcaView(View):
    temp = 'home/brca.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class CancerView(View):
    temp = 'home/cancer.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class HrdView(View):
    temp = 'home/hrd.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class tmbView(View):
    temp = 'home/tmb.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class HistView(View):
    temp = 'home/histologic.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class NiptView(View):
    temp = 'home/nipt.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class PgdView(View):
    temp = 'home/pgd.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class PndView(View):
    temp = 'home/pnd.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class PanelTView(View):
    temp = 'home/panelT.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class NgsView(View):
    temp = 'home/ngs.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class SyndromXView(View):
    temp = 'home/syndromx.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class AzoView(View):
    temp = 'home/azo.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class SmaView(View):
    temp = 'home/sma.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class BcsView(View):
    temp = 'home/bcs.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class CytogeneticView(View):
    temp = 'home/Cytogenetic.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class MicrobiomeView(View):
    temp = 'home/Microbiome.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


class TalentView(View):
    temp = 'home/talent.html'

    def get(self, request):
        return render(request, self.temp)

    def post(self, request):
        return render(request, self.temp)


def partial_header(request):
    return render(request, 'shared/partial_header.html')


def partial_footer(request):
    return render(request, 'shared/partial_footer.html')
