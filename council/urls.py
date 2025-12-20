from django.urls import path

from . import views

app_name = 'council'

urlpatterns = [
    # Step 1: Initial form
    path('consultation/', views.ReservationStep1View.as_view(), name='step1_initial'),
    path('con/', views.ReservationStep1View.as_view(), name='con'),  # Alias

    # Step 2: Select time
    path('select-time/', views.ReservationStep2View.as_view(), name='step2_select_time'),

    # Step 3: Phone verification
    path('verify-phone/', views.ReservationStep3View.as_view(), name='step3_verify_phone'),

    # Step 4: Review
    path('review/<str:tracking_code>/', views.ReservationStep4View.as_view(), name='step4_review'),

    # Final: Receipt
    path('receipt/<str:tracking_code>/', views.ReservationReceiptView.as_view(), name='final_receipt'),

    # AJAX endpoints
    path('api/check-slot/<int:slot_id>/', views.check_slot_availability, name='check_slot_availability'),
    path('api/slots/<int:service_type_id>/', views.get_service_slots_api, name='get_service_slots_api'),

    # reservation PDF
    path("receipt/<str:tracking_code>/pdf/", views.ReservationReceiptPDFView.as_view(), name="receipt_pdf"),
]
