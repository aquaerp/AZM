import base64
from decimal import Decimal

from django.utils import timezone


def encode_tlv(fields):
    payload = bytearray()
    for tag, value in fields:
        encoded = str(value).encode("utf-8")
        if not 0 < tag < 256 or len(encoded) > 255:
            raise ValueError("قيمة TLV خارج النطاق المسموح به.")
        payload.extend((tag, len(encoded)))
        payload.extend(encoded)
    return bytes(payload)


def phase_one_qr_payload(invoice):
    if not invoice.issued_at:
        raise ValueError("يجب إصدار الفاتورة قبل إنشاء QR.")
    if not invoice.workshop.tax_number:
        raise ValueError("الرقم الضريبي للورشة مطلوب لإنشاء QR.")
    issued_at = invoice.issued_at
    if timezone.is_naive(issued_at):
        issued_at = timezone.make_aware(issued_at, timezone.get_current_timezone())
    fields = (
        (1, invoice.workshop.legal_name or invoice.workshop.name),
        (2, invoice.workshop.tax_number),
        (3, issued_at.isoformat()),
        (4, f"{Decimal(invoice.total):.2f}"),
        (5, f"{Decimal(invoice.tax_amount):.2f}"),
    )
    return base64.b64encode(encode_tlv(fields)).decode("ascii")
