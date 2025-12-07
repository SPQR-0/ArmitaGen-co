from django import urls
from django.urls import path

from .views import *

app_name = 'services'

urlpatterns = [
    path('', IndexView.as_view(), name='home'),
    path('test', TestView.as_view(), name='test')
]