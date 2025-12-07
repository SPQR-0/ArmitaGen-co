from io import BytesIO

import arabic_reshaper
import jdatetime
from bidi.algorithm import get_display
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)


class PDFGenerator:
    def __init__(self):
        import os
        from django.conf import settings

        font_filename = 'Vazirmatn-Regular.ttf'

        font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', font_filename)

        self.font_name = 'Helvetica'

        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('PersianFont', font_path))
                self.font_name = 'PersianFont'
            except Exception as e:
                print(f"⚠️ Font File Error: {e}")
        else:
            print(f"⚠️ Font not found at: {font_path}")

        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _fix_text(self, text):
        if text is None:
            return ""

        text = str(text)

        if self.font_name == 'Helvetica':
            return text

        try:
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            return bidi_text
        except Exception:
            return text

    def _setup_styles(self):

        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontName=self.font_name,
            fontSize=24,
            textColor=colors.HexColor('#2d3748'),
            alignment=1,
            spaceAfter=30,
            leading=36
        )

        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontName=self.font_name,
            fontSize=11,
            textColor=colors.HexColor('#4a5568'),
            alignment=2,
            leading=16
        )

        self.label_style = ParagraphStyle(
            'CustomLabel',
            parent=self.styles['Normal'],
            fontName=self.font_name,
            fontSize=9,
            textColor=colors.HexColor('#a0aec0'),
            alignment=2,
            leading=14
        )

    def generate_reservation_receipt_user(self, reservation):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm
        )

        elements = []

        # Logo
        elements.append(Spacer(1, 1 * cm))
        logo_text = Paragraph(
            f'<para align="center">{self._fix_text("[محل لوگو]")}</para>',
            self.label_style
        )
        elements.append(logo_text)
        elements.append(Spacer(1, 1.5 * cm))

        # عنوان
        title = Paragraph(self._fix_text('رسید رزرو نوبت'), self.title_style)
        elements.append(title)

        # کد پیگیری
        tracking_box = self._create_tracking_box(reservation.tracking_code)
        elements.append(tracking_box)
        elements.append(Spacer(1, 1 * cm))

        # اطلاعات کاربر
        user_info = self._create_info_section(
            'اطلاعات شخصی',
            [
                ('نام و نام خانوادگی', reservation.full_name),
                ('شماره تلفن', reservation.phone_number),
            ]
        )
        elements.append(user_info)
        elements.append(Spacer(1, 0.8 * cm))

        # اطلاعات نوبت
        jalali_date = jdatetime.date.fromgregorian(date=reservation.time_slot.date)
        time_str = f"{reservation.time_slot.start_time.strftime('%H:%M')} - {reservation.time_slot.end_time.strftime('%H:%M')}"

        appointment_info = self._create_info_section(
            'اطلاعات نوبت',
            [
                ('نوع خدمت', reservation.service_type.name),
                ('تاریخ', jalali_date.strftime('%Y/%m/%d')),
                ('ساعت', time_str),
                ('وضعیت', reservation.get_status_display()),
            ]
        )
        elements.append(appointment_info)
        elements.append(Spacer(1, 0.8 * cm))

        # اطلاعات پرداخت
        payment = reservation.payments.filter(status='success').first()
        if payment:
            paid_date = jdatetime.datetime.fromgregorian(datetime=payment.paid_at).strftime(
                '%Y/%m/%d - %H:%M') if payment.paid_at else '-'
            payment_info = self._create_info_section(
                'اطلاعات پرداخت',
                [
                    ('مبلغ', f"{reservation.service_type.price:,} تومان"),
                    ('وضعیت', 'پرداخت شده ✓'),
                    ('تاریخ پرداخت', paid_date),
                ]
            )
            elements.append(payment_info)

        # فوتر
        elements.append(Spacer(1, 2 * cm))
        footer = Paragraph(
            f'<para align="center">{self._fix_text("این رسید به صورت الکترونیکی صادر شده است")}</para>',
            self.label_style
        )
        elements.append(footer)

        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{reservation.tracking_code}.pdf"'
        return response

    def generate_reservation_receipt_admin(self, reservation):
        """
        PDF رسید برای ادمین - با جزئیات کامل
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=2 * cm,
                                bottomMargin=2 * cm)

        elements = []

        elements.append(Spacer(1, 0.5 * cm))
        logo_text = Paragraph(f'<para align="center">{self._fix_text("[محل لوگو - نسخه ادمین]")}</para>',
                              self.label_style)
        elements.append(logo_text)
        elements.append(Spacer(1, 1 * cm))

        title = Paragraph(self._fix_text('گزارش کامل رزرو'), self.title_style)
        elements.append(title)

        tracking_box = self._create_tracking_box(reservation.tracking_code)
        elements.append(tracking_box)
        elements.append(Spacer(1, 0.8 * cm))

        # اطلاعات کاربر
        user_info = self._create_info_section(
            'اطلاعات کاربر',
            [
                ('شناسه رزرو', f"#{reservation.id}"),
                ('نام و نام خانوادگی', reservation.full_name),
                ('شماره تلفن', reservation.phone_number),
                ('ایمیل', reservation.email or '-'),
                ('کاربر ثبت شده', reservation.user.full_name if reservation.user else '-'),
            ]
        )
        elements.append(user_info)
        elements.append(Spacer(1, 0.6 * cm))

        # اطلاعات نوبت
        jalali_date = jdatetime.date.fromgregorian(date=reservation.time_slot.date)
        time_str = f"{reservation.time_slot.start_time.strftime('%H:%M')} - {reservation.time_slot.end_time.strftime('%H:%M')}"

        appointment_info = self._create_info_section(
            'اطلاعات نوبت',
            [
                ('نوع خدمت', reservation.service_type.name),
                ('عنوان مشاوره', reservation.consultation_topic.name if reservation.consultation_topic else '-'),
                ('تاریخ (میلادی)', str(reservation.time_slot.date)),
                ('تاریخ (شمسی)', jalali_date.strftime('%Y/%m/%d')),
                ('ساعت', time_str),
                ('وضعیت رزرو', reservation.get_status_display()),
                ('وضعیت پرداخت', reservation.get_payment_status_display()),
            ]
        )
        elements.append(appointment_info)
        elements.append(Spacer(1, 0.6 * cm))

        # تاریخ‌ها
        created_at = jdatetime.datetime.fromgregorian(datetime=reservation.created_at).strftime('%Y/%m/%d - %H:%M:%S')
        verified_at = jdatetime.datetime.fromgregorian(datetime=reservation.phone_verified_at).strftime(
            '%Y/%m/%d - %H:%M:%S') if reservation.phone_verified_at else '-'

        dates_info = self._create_info_section(
            'تاریخچه',
            [
                ('تاریخ رزرو', created_at),
                ('تایید شماره', verified_at),
            ]
        )
        elements.append(dates_info)
        elements.append(Spacer(1, 0.6 * cm))

        # پیام کاربر
        if reservation.message:
            message_section = self._create_info_section(
                'پیام کاربر',
                [('متن پیام', reservation.message)]
            )
            elements.append(message_section)
            elements.append(Spacer(1, 0.6 * cm))

        # اطلاعات پرداخت
        payment = reservation.payments.filter(status='success').first()
        if payment:
            paid_at = jdatetime.datetime.fromgregorian(datetime=payment.paid_at).strftime(
                '%Y/%m/%d - %H:%M:%S') if payment.paid_at else '-'
            payment_info = self._create_info_section(
                'جزئیات پرداخت',
                [
                    ('شناسه پرداخت', f"#{payment.id}"),
                    ('مبلغ', f"{payment.amount:,} تومان"),
                    ('وضعیت', payment.get_status_display()),
                    ('کد رهگیری', payment.reference_code or '-'),
                    ('کد پیگیری بانک', payment.tracking_code or '-'),
                    ('تاریخ پرداخت', paid_at),
                ]
            )
            elements.append(payment_info)

        elements.append(Spacer(1, 1.5 * cm))

        current_date = jdatetime.datetime.now().strftime("%Y/%m/%d - %H:%M:%S")
        footer_text = f"گزارش ایجاد شده در: {current_date}"
        footer = Paragraph(
            f'<para align="center">{self._fix_text(footer_text)}</para>',
            self.label_style
        )
        elements.append(footer)

        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="admin_receipt_{reservation.tracking_code}.pdf"'
        return response

    def _create_tracking_box(self, tracking_code):
        """باکس مینیمال برای کد پیگیری"""
        fixed_code = self._fix_text(tracking_code)
        data = [[Paragraph(f'<para align="center"><b>{fixed_code}</b></para>', self.body_style)]]

        table = Table(data, colWidths=[10 * cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ]))
        return table

    def _create_info_section(self, title, items):
        """ساخت بخش اطلاعات به صورت مینیمال"""
        data = []

        # عنوان بخش
        fixed_title = self._fix_text(title)
        data.append([
            Paragraph(f'<para align="right"><b>{fixed_title}</b></para>', self.body_style),
            ''
        ])

        # آیتم‌ها (بسیار مهم: هم عنوان و هم مقدار باید فیکس شوند)
        for label, value in items:
            fixed_value = self._fix_text(value)
            fixed_label = self._fix_text(label)

            data.append([
                Paragraph(f'<para align="right">{fixed_value}</para>', self.body_style),
                Paragraph(f'<para align="right"><font color="#a0aec0">{fixed_label}</font></para>', self.label_style),
            ])

        table = Table(data, colWidths=[10 * cm, 5 * cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f7fafc')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#e2e8f0')),
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, colors.HexColor('#f7fafc')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ]))
        return table


# Helper Functions
def generate_user_receipt_pdf(reservation):
    generator = PDFGenerator()
    return generator.generate_reservation_receipt_user(reservation)


def generate_admin_receipt_pdf(reservation):
    generator = PDFGenerator()
    return generator.generate_reservation_receipt_admin(reservation)
