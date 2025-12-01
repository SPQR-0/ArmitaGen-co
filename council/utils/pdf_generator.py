# """
# PDF Report Generator for Reservation Confirmations
# Uses ReportLab library for Persian PDF generation
# """
#
# from datetime import datetime
# from io import BytesIO
#
# from django.conf import settings
# from django.http import HttpResponse
# from reportlab.lib import colors
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.units import cm
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont
# from reportlab.pdfgen import canvas
# from reportlab.platypus import Table, TableStyle
#
#
# class ReservationPDFGenerator:
#     """
#     Generate PDF report for reservation confirmation
#     Includes all reservation details and QR code
#     """
#
#     def __init__(self, reservation):
#         """
#         Initialize PDF generator with reservation instance
#
#         Args:
#             reservation: Reservation model instance
#         """
#         self.reservation = reservation
#         self.buffer = BytesIO()
#         self.page_width, self.page_height = A4
#         self.margin = 2 * cm
#
#         # Register Persian font (you need to have the font file)
#         # Example: IRANSans or Vazir font
#         try:
#             pdfmetrics.registerFont(
#                 TTFont('Persian', settings.PERSIAN_FONT_PATH)
#             )
#             self.font_name = 'Persian'
#         except:
#             # Fallback to default font if Persian font not available
#             self.font_name = 'Helvetica'
#
#     def generate(self):
#         """
#         Generate PDF and return as HttpResponse
#
#         Returns:
#             HttpResponse: PDF file response
#         """
#         # Create canvas
#         p = canvas.Canvas(self.buffer, pagesize=A4)
#
#         # Draw content
#         self._draw_header(p)
#         self._draw_reservation_info(p)
#         self._draw_contact_info(p)
#         self._draw_payment_info(p)
#         self._draw_footer(p)
#
#         # Finalize PDF
#         p.showPage()
#         p.save()
#
#         # Get PDF value
#         pdf_value = self.buffer.getvalue()
#         self.buffer.close()
#
#         # Create response
#         response = HttpResponse(pdf_value, content_type='application/pdf')
#         filename = f'reservation_{self.reservation.tracking_code}.pdf'
#         response['Content-Disposition'] = f'attachment; filename="{filename}"'
#
#         return response
#
#     def _draw_header(self, canvas_obj):
#         """Draw PDF header with logo and title"""
#         y_position = self.page_height - self.margin
#
#         # Title
#         canvas_obj.setFont(self.font_name, 20)
#         canvas_obj.drawString(
#             self.page_width / 2 - 100,
#             y_position,
#             'تایید رزرو مشاوره ژنتیک'
#         )
#
#         # Draw line
#         y_position -= 1 * cm
#         canvas_obj.line(
#             self.margin,
#             y_position,
#             self.page_width - self.margin,
#             y_position
#         )
#
#         # Logo placeholder (if you have a logo)
#         # canvas_obj.drawImage('path/to/logo.png', x, y, width, height)
#
#     def _draw_reservation_info(self, canvas_obj):
#         """Draw reservation information section"""
#         y_position = self.page_height - self.margin - 3 * cm
#
#         # Section title
#         canvas_obj.setFont(self.font_name, 14)
#         canvas_obj.drawString(self.margin, y_position, 'اطلاعات رزرو')
#         y_position -= 1 * cm
#
#         # Reservation details
#         canvas_obj.setFont(self.font_name, 11)
#
#         details = [
#             ('کد پیگیری', self.reservation.tracking_code),
#             ('نوع خدمت', self.reservation.service_type.name),
#             ('تاریخ', str(self.reservation.time_slot.date)),
#             (
#                 'ساعت',
#                 f"{self.reservation.time_slot.start_time} - "
#                 f"{self.reservation.time_slot.end_time}"
#             ),
#             ('وضعیت', self.reservation.get_status_display()),
#             ('تاریخ رزرو', self.reservation.created_at.strftime('%Y-%m-%d %H:%M')),
#         ]
#
#         for label, value in details:
#             canvas_obj.drawRightString(
#                 self.page_width - self.margin - 100,
#                 y_position,
#                 f"{label}:"
#             )
#             canvas_obj.drawString(
#                 self.page_width - self.margin - 95,
#                 y_position,
#                 str(value)
#             )
#             y_position -= 0.6 * cm
#
#     def _draw_contact_info(self, canvas_obj):
#         """Draw contact information section"""
#         y_position = self.page_height - self.margin - 10 * cm
#
#         # Section title
#         canvas_obj.setFont(self.font_name, 14)
#         canvas_obj.drawString(self.margin, y_position, 'اطلاعات تماس')
#         y_position -= 1 * cm
#
#         # Contact details
#         canvas_obj.setFont(self.font_name, 11)
#
#         contact_details = [
#             ('نام و نام خانوادگی', self.reservation.full_name),
#             ('شماره تلفن', self.reservation.phone_number),
#         ]
#
#         if self.reservation.national_code:
#             contact_details.append(('کد ملی', self.reservation.national_code))
#
#         if self.reservation.email:
#             contact_details.append(('ایمیل', self.reservation.email))
#
#         for label, value in contact_details:
#             canvas_obj.drawRightString(
#                 self.page_width - self.margin - 100,
#                 y_position,
#                 f"{label}:"
#             )
#             canvas_obj.drawString(
#                 self.page_width - self.margin - 95,
#                 y_position,
#                 str(value)
#             )
#             y_position -= 0.6 * cm
#
#         # Message if exists
#         if self.reservation.message:
#             y_position -= 0.5 * cm
#             canvas_obj.drawString(self.margin, y_position, 'یادداشت:')
#             y_position -= 0.6 * cm
#
#             # Wrap long messages
#             message_lines = self._wrap_text(
#                 self.reservation.message,
#                 canvas_obj,
#                 self.page_width - 2 * self.margin
#             )
#             for line in message_lines:
#                 canvas_obj.drawString(self.margin + 0.5 * cm, y_position, line)
#                 y_position -= 0.5 * cm
#
#     def _draw_payment_info(self, canvas_obj):
#         """Draw payment information section"""
#         y_position = self.page_height - self.margin - 16 * cm
#
#         # Section title
#         canvas_obj.setFont(self.font_name, 14)
#         canvas_obj.drawString(self.margin, y_position, 'اطلاعات پرداخت')
#         y_position -= 1 * cm
#
#         # Payment details
#         canvas_obj.setFont(self.font_name, 11)
#
#         payment_details = [
#             ('مبلغ', f"{self.reservation.service_type.price:,} تومان"),
#             ('وضعیت پرداخت', self.reservation.get_payment_status_display()),
#         ]
#
#         # Add payment reference if paid
#         if self.reservation.payment_status == 'paid':
#             latest_payment = self.reservation.payments.filter(
#                 status='success'
#             ).order_by('-paid_at').first()
#
#             if latest_payment and latest_payment.ref_id:
#                 payment_details.append(
#                     ('کد پیگیری بانک', latest_payment.ref_id)
#                 )
#                 if latest_payment.paid_at:
#                     payment_details.append(
#                         ('تاریخ پرداخت', latest_payment.paid_at.strftime('%Y-%m-%d %H:%M'))
#                     )
#
#         for label, value in payment_details:
#             canvas_obj.drawRightString(
#                 self.page_width - self.margin - 100,
#                 y_position,
#                 f"{label}:"
#             )
#             canvas_obj.drawString(
#                 self.page_width - self.margin - 95,
#                 y_position,
#                 str(value)
#             )
#             y_position -= 0.6 * cm
#
#     def _draw_footer(self, canvas_obj):
#         """Draw PDF footer with contact information"""
#         y_position = self.margin + 1 * cm
#
#         # Draw line
#         canvas_obj.line(
#             self.margin,
#             y_position,
#             self.page_width - self.margin,
#             y_position
#         )
#
#         # Footer text
#         y_position -= 0.7 * cm
#         canvas_obj.setFont(self.font_name, 9)
#         canvas_obj.drawCentredString(
#             self.page_width / 2,
#             y_position,
#             'این گزارش به صورت خودکار تولید شده است'
#         )
#
#         y_position -= 0.5 * cm
#         canvas_obj.drawCentredString(
#             self.page_width / 2,
#             y_position,
#             f'تاریخ تولید گزارش: {datetime.now().strftime("%Y-%m-%d %H:%M")}'
#         )
#
#         # Add QR code placeholder (you can use qrcode library)
#         # canvas_obj.drawImage('qr_code.png', x, y, width, height)
#
#     def _wrap_text(self, text, canvas_obj, max_width):
#         """
#         Wrap text to fit within max_width
#
#         Args:
#             text: Text to wrap
#             canvas_obj: Canvas object
#             max_width: Maximum width in points
#
#         Returns:
#             list: List of wrapped text lines
#         """
#         words = text.split()
#         lines = []
#         current_line = []
#
#         for word in words:
#             test_line = ' '.join(current_line + [word])
#             if canvas_obj.stringWidth(test_line, self.font_name, 11) <= max_width:
#                 current_line.append(word)
#             else:
#                 if current_line:
#                     lines.append(' '.join(current_line))
#                 current_line = [word]
#
#         if current_line:
#             lines.append(' '.join(current_line))
#
#         return lines
#
#
# def generate_reservation_pdf(reservation):
#     """
#     Convenience function to generate reservation PDF
#
#     Args:
#         reservation: Reservation model instance
#
#     Returns:
#         HttpResponse: PDF file response
#
#     Example:
#         response = generate_reservation_pdf(reservation)
#         return response
#     """
#     generator = ReservationPDFGenerator(reservation)
#     return generator.generate()
#
#
# # Alternative: Simple text-based PDF (if ReportLab not available)
# def generate_simple_pdf(reservation):
#     """
#     Generate simple text-based PDF using built-in canvas
#     Fallback option if ReportLab is not available
#     """
#     buffer = BytesIO()
#     p = canvas.Canvas(buffer, pagesize=A4)
#
#     # Simple text output
#     y = 800
#     p.drawString(100, y, f"Tracking Code: {reservation.tracking_code}")
#     y -= 20
#     p.drawString(100, y, f"Service: {reservation.service_type.name}")
#     y -= 20
#     p.drawString(100, y, f"Name: {reservation.full_name}")
#     y -= 20
#     p.drawString(100, y, f"Phone: {reservation.phone_number}")
#     y -= 20
#     p.drawString(100, y, f"Date: {reservation.time_slot.date}")
#     y -= 20
#     p.drawString(100, y, f"Time: {reservation.time_slot.start_time}")
#     y -= 20
#     p.drawString(100, y, f"Status: {reservation.get_status_display()}")
#
#     p.showPage()
#     p.save()
#
#     pdf = buffer.getvalue()
#     buffer.close()
#
#     response = HttpResponse(pdf, content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename="reservation_{reservation.tracking_code}.pdf"'
#
#     return response
