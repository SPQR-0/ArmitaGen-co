from django.urls import path
from django import urls
from .views import *


app_name = 'team'

urlpatterns = [
    path('about-us/', AboutUsView.as_view(), name='about-us'),
    path('contact-us', ContactUsView.as_view(), name='contact-us')
]