from django.urls import path

from .views import *

app_name = 'council'

urlpatterns = [
    path('council/', CouncilView.as_view(), name='con'),
    path('council/success/', lambda request: render(request, 'council/success.html'), name='con_success'),
]
