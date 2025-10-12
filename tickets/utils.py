import io
import os
from django.conf import settings
from django.utils import timezone

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import qrcode

# ---- регистрация шрифтов (один раз на процесс) ----
_FONT_REG_DONE = False
_FONT_REGULAR = "DejaVu"
_FONT_BOLD = "DejaVu-Bold"

def _ensure_fonts():
    global _FONT_REG_DONE
    if _FONT_REG_DONE:
        return
    fonts_dir = os.path.join(settings.BASE_DIR, "fonts")
    regular_path = os.path.join(fonts_dir, "DejaVuSans.ttf")
    bold_path = os.path.join(fonts_dir, "DejaVuSans-Bold.ttf")
    pdfmetrics.registerFont(TTFont(_FONT_REGULAR, regular_path))
    pdfmetrics.registerFont(TTFont(_FONT_BOLD, bold_path))
    _FONT_REG_DONE = True


def _format_dt(dt):
    if not dt:
        return ""
    dt = timezone.localtime(dt)
    return dt.strftime("%d.%m.%Y %H:%M")


def build_ticket_pdf(ticket):
    """
    Генерирует PDF-билет с QR-кодом и основными реквизитами.
    Возвращает bytes.
    """
    _ensure_fonts()  # <- ВАЖНО: шрифты готовы

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_left = 20 * mm
    margin_top = height - 20 * mm

    # Заголовок
    c.setFont(_FONT_BOLD, 20)
    c.drawString(margin_left, margin_top, "Электронный билет")

    # Основные поля
    y = margin_top - 15 * mm
    c.setFont(_FONT_BOLD, 14)
    c.drawString(margin_left, y, ticket.event.title)
    y -= 7 * mm

    c.setFont(_FONT_REGULAR, 11)
    c.drawString(margin_left, y, f"Категория: {ticket.event.category.name}")
    y -= 6 * mm
    c.drawString(margin_left, y, f"Дата и время: {_format_dt(ticket.event.starts_at)}")
    y -= 6 * mm
    if ticket.event.duration_minutes:
        c.drawString(margin_left, y, f"Длительность: ~{ticket.event.duration_minutes} мин.")
        y -= 6 * mm
    c.drawString(margin_left, y, f"Место проведения: {ticket.event.location}")
    y -= 10 * mm

    # Детали билета
    c.setFont(_FONT_BOLD, 12)
    c.drawString(margin_left, y, "Детали билета")
    y -= 7 * mm

    c.setFont(_FONT_REGULAR, 11)
    c.drawString(margin_left, y, f"Номер билета: {ticket.pk}")
    y -= 6 * mm
    c.drawString(margin_left, y, f"Номер заказа: {ticket.order_id}")
    y -= 6 * mm
    c.drawString(margin_left, y, f"Покупатель: {ticket.user.get_full_name() or ticket.user.username}")
    y -= 6 * mm
    c.drawString(margin_left, y, f"Тариф: {ticket.event_tariff.tariff.name}")
    y -= 6 * mm
    c.drawString(margin_left, y, f"Цена: {ticket.event_tariff.price} ₽")
    y -= 10 * mm

    # QR-код
    qr_payload = f"TICKET:{ticket.pk}|HASH:{ticket.qr_hash}|EVENT:{ticket.event_id}"

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(qr_payload)
    qr.make(fit=True)

    # превращаем в PNG-байты (ReportLab так любит)
    qr_img = qr.make_image(fill_color="black", back_color="white").get_image()
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    qr_size = 50 * mm
    c.drawImage(
        ImageReader(qr_buffer),
        width - qr_size - 20 * mm,
        margin_top - qr_size,
        qr_size,
        qr_size,
        mask='auto'
    )

    # Подвал
    c.setFont(_FONT_REGULAR, 9)
    footer_y = 15 * mm
    c.drawString(margin_left, footer_y, "Покажите QR-код на входе. Один QR — один проход.")
    c.drawString(margin_left, footer_y - 5 * mm, "Организатор может проверить подлинность по номеру и QR-коду.")

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
