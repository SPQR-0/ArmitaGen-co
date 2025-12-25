from django import urls
from django.urls import path

from .views import *

app_name = 'team'

urlpatterns = [
    path('about-us/', AboutUsView.as_view(), name='about-us'),
    path('contact-us', ContactUsView.as_view(), name='contact-us'),
    path('team/', TeamView.as_view(), name='team'),
    path('soon/', SoonView.as_view(), name='soon')
]