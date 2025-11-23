# app_name/admin.py

from django.contrib import admin
from .models import GeneticConsultationRequest


@admin.register(GeneticConsultationRequest)
class GeneticConsultationRequestAdmin(admin.ModelAdmin):
    pass