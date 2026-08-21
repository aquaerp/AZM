import os
from io import BytesIO
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display
from django.core.files.base import ContentFile
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader

from .zatca import phase_one_qr_payload


FONT_NAME = "AzmArabic"
FONT_CANDIDATES = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
)


def rtl(value):
    return get_display(arabic_reshaper.reshape(str(value or "")))


def resolve_arabic_font_path():
    configured = os.environ.get("AZM_ARABIC_FONT_PATH")
    candidates = (Path(configured),) + FONT_CANDIDATES if configured else FONT_CANDIDATES
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("لم يُعثر على خط عربي. اضبط AZM_ARABIC_FONT_PATH أو ثبّت fonts-dejavu-core.")


def ensure_font():
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(resolve_arabic_font_path())))


def generate_invoice_pdf(invoice, language="ar"):
    """Generate a complete multi-page invoice and persist it on the invoice."""

    english = language == "en"
    if not english:
        ensure_font()
    font_name = "Helvetica" if english else FONT_NAME
    title_font = "Helvetica-Bold" if english else FONT_NAME
    display = str if english else rtl
    workshop = invoice.workshop
    seller_name = workshop.legal_name or workshop.name
    address_parts = [workshop.building_number, workshop.street, workshop.district, workshop.city, workshop.postal_code]
    invoice_address = workshop.national_address or "، ".join(str(part) for part in address_parts if part) or "-"
    customer = invoice.job_card.customer
    vehicle = invoice.job_card.vehicle
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    width, height = A4
    page_number = 0

    labels = {
        "title": "Tax Invoice" if english else "فاتورة ضريبية",
        "invoice": "Invoice" if english else "رقم الفاتورة",
        "customer": "Customer" if english else "العميل",
        "vehicle": "Vehicle" if english else "المركبة",
        "issued": "Issued" if english else "تاريخ الإصدار",
        "vat_no": "VAT number" if english else "الرقم الضريبي",
        "cr": "Commercial registration" if english else "السجل التجاري",
        "address": "National address" if english else "العنوان الوطني",
        "description": "Description" if english else "الوصف",
        "quantity": "Quantity" if english else "الكمية",
        "price": "Price" if english else "السعر",
        "total": "Total" if english else "الإجمالي",
        "subtotal": "Subtotal" if english else "الإجمالي قبل الضريبة",
        "vat": "VAT" if english else "ضريبة القيمة المضافة",
        "due": "Total due" if english else "الإجمالي المستحق",
        "paid": "Paid" if english else "المدفوع",
    }

    def draw_text(x, y, text, *, right=False):
        rendered = display(text)
        (canvas.drawRightString if right else canvas.drawString)(x, y, rendered)

    def draw_page_header(include_parties):
        nonlocal page_number
        page_number += 1
        canvas.setFillColor(colors.HexColor("#07345B"))
        canvas.rect(0, height - 105, width, 105, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont(title_font, 22)
        header_x = 130 if english else width - 120
        if workshop.logo:
            try:
                workshop.logo.open("rb")
                canvas.drawImage(ImageReader(workshop.logo), 42, height - 91, width=76, height=70, preserveAspectRatio=True, anchor="c", mask="auto")
            except (OSError, ValueError):
                pass
        draw_text(header_x, height - 48, f"{labels['title']} - {seller_name}", right=not english)
        canvas.setFont(font_name, 10)
        draw_text(header_x, height - 72, f"{labels['invoice']}: {invoice.invoice_number}", right=not english)
        draw_text(header_x, height - 89, f"{labels['vat_no']}: {workshop.tax_number or '-'}", right=not english)
        if include_parties and workshop.tax_number:
            qr = QrCodeWidget(phase_one_qr_payload(invoice))
            x1, y1, x2, y2 = qr.getBounds()
            size = 76
            drawing = Drawing(size, size, transform=[size / (x2 - x1), 0, 0, size / (y2 - y1), 0, 0])
            drawing.add(qr)
            renderPDF.draw(drawing, canvas, width - 105, height - 96)
        y = height - 130
        canvas.setFillColor(colors.HexColor("#1B384D"))
        canvas.setFont(font_name, 10)
        if include_parties:
            details = [
                f"{labels['customer']}: {customer.name}",
                f"{labels['vehicle']}: {vehicle.make} {vehicle.model} - {vehicle.license_plate}",
                f"{labels['issued']}: {invoice.issued_at or '-'}",
                f"{labels['cr']}: {workshop.commercial_registration or '-'}",
                f"{labels['address']}: {invoice_address[:110]}",
                f"{'Contact' if english else 'الاتصال'}: {workshop.phone or '-'} {workshop.email or ''}",
            ]
            for detail in details:
                draw_text(width - 42 if not english else 42, y, detail, right=not english)
                y -= 17
        return y - 12

    def draw_table_header(y):
        columns = [42, 275, 365, 445, 545]
        canvas.setFillColor(colors.HexColor("#0C6193"))
        canvas.rect(42, y, 503, 24, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont(font_name, 9)
        headers = (labels["description"], labels["quantity"], labels["price"], labels["total"])
        if english:
            positions = ((50, headers[0]), (285, headers[1]), (375, headers[2]), (455, headers[3]))
            for x, text in positions:
                draw_text(x, y + 7, text)
        else:
            positions = ((columns[1] - 8, headers[0]), (columns[2] - 8, headers[1]), (columns[3] - 8, headers[2]), (columns[4] - 8, headers[3]))
            for x, text in positions:
                draw_text(x, y + 7, text, right=True)
        return y - 22

    def draw_footer():
        footer = "Thank you for choosing Azm." if english else "شكرًا لثقتكم بعزم"
        canvas.setFillColor(colors.HexColor("#607080"))
        canvas.setFont(font_name, 8)
        canvas.drawCentredString(width / 2, 42, display(f"{footer} - {page_number}"))

    canvas.setTitle(invoice.invoice_number)
    y = draw_table_header(draw_page_header(include_parties=True))
    columns = [42, 275, 365, 445, 545]
    canvas.setFont(font_name, 9)
    for index, line in enumerate(invoice.lines.all()):
        if y < 105:
            draw_footer()
            canvas.showPage()
            y = draw_table_header(draw_page_header(include_parties=False))
            canvas.setFont(font_name, 9)
        canvas.setFillColor(colors.HexColor("#F3F7FA") if index % 2 else colors.white)
        canvas.rect(42, y, 503, 22, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#1B384D"))
        draw_text(50 if english else columns[1] - 8, y + 6, line.description[:48], right=not english)
        canvas.drawRightString(columns[2] - 8, y + 6, f"{line.quantity:g}")
        canvas.drawRightString(columns[3] - 8, y + 6, f"{line.unit_price:.2f}")
        canvas.drawRightString(columns[4] - 8, y + 6, f"{line.line_total:.2f}")
        y -= 22

    if y < 145:
        draw_footer()
        canvas.showPage()
        y = draw_page_header(include_parties=False) - 10
    canvas.setStrokeColor(colors.HexColor("#D8E2E9"))
    canvas.line(330, y, 545, y)
    y -= 22
    totals = ((labels["subtotal"], invoice.subtotal), (labels["vat"], invoice.tax_amount), (labels["due"], invoice.total), (labels["paid"], invoice.amount_paid))
    canvas.setFont(font_name, 10)
    for label, amount in totals:
        canvas.setFillColor(colors.HexColor("#1B384D"))
        draw_text(330 if english else 455, y, label, right=not english)
        canvas.drawRightString(545, y, f"{amount:.2f} SAR")
        y -= 20

    draw_footer()
    canvas.save()
    invoice.pdf_file.save(f"{invoice.invoice_number}.pdf", ContentFile(buffer.getvalue()), save=False)
    invoice.save(update_fields=("pdf_file", "updated_at"))
    return invoice
