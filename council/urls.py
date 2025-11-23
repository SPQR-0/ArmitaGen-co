from django.urls import path
from django import urls
from .views import *


app_name = 'council'

urlpatterns = [
    path('council/', CouncilView.as_view(), name='con'),
]