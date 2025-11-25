from django.urls import path

from .views import *

app_name = 'council'

urlpatterns = [
    path('consultation/', CouncilView.as_view(), name='con'),
    path('success/', SuccessView.as_view(), name='con_success'),
]
