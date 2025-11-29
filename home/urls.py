from django.urls import path

from .views import *

app_name = 'home'

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('test', TestView.as_view(), name='test'),
    path('brca', BrcaView.as_view(), name='brca'),
    path('cancer', CancerView.as_view(), name='cancer'),
    path('hrd', HrdView.as_view(), name='hrd'),
    path('tmb', tmbView.as_view(), name='tmb'),
    path('histologic', HistView.as_view(), name='hist'),
    path('nipt', NiptView.as_view(), name='nipt'),
    path('pgd', PgdView.as_view(), name='pgd'),
    path('pnd', PndView.as_view(), name='pnd'),
    path('panelT', PanelTView.as_view(), name='panelT'),
    path('ngs', NgsView.as_view(), name='ngs'),
    path('syndromx', SyndromXView.as_view(), name='syndromx'),
    path('azo', AzoView.as_view(), name='azo'),
    path('sma', SmaView.as_view(), name='sma'),
    path('bcs', BcsView.as_view(), name='bcs'),
    path('Cytogenetic', CytogeneticView.as_view(), name='Cytogenetic'),
    path('Microbiome', MicrobiomeView.as_view(), name='Microbiome'),
    path('talent', TalentView.as_view(), name='talent'),
]
