from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from inventory.models import PartUsage
from workshop.models import JobCard

from .models import Expense, Invoice, InvoiceLine, Payment


MONEY = Decimal("0.01")


def recalculate_invoice(invoice: Invoice) -> Invoice:
    subtotal = invoice.lines.aggregate(total=Sum("line_total"))["total"] or Decimal("0.00")
    invoice.subtotal = subtotal.quantize(MONEY)
    invoice.tax_amount = (invoice.subtotal * invoice.vat_rate / Decimal("100")).quantize(MONEY, rounding=ROUND_HALF_UP)
    invoice.total = (invoice.subtotal + invoice.tax_amount).quantize(MONEY)
    amount_paid = invoice.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    invoice.amount_paid = amount_paid.quantize(MONEY)
    if invoice.status != Invoice.Status.VOID:
        if invoice.amount_paid >= invoice.total and invoice.total > 0:
            invoice.status = Invoice.Status.PAID
        elif invoice.amount_paid > 0:
            invoice.status = Invoice.Status.PARTIAL
    invoice.save(update_fields=("subtotal", "tax_amount", "total", "amount_paid", "status", "updated_at"))
    return invoice


@transaction.atomic
def create_invoice_from_job(job_card: JobCard) -> Invoice:
    if job_card.status not in (JobCard.Status.READY, JobCard.Status.DELIVERED):
        raise ValueError("لا يمكن إصدار فاتورة قبل أن تصبح بطاقة العمل جاهزة أو مسلّمة.")
    if hasattr(job_card, "invoice"):
        return job_card.invoice
    invoice = Invoice.objects.create(workshop=job_card.workshop, job_card=job_card, due_at=date.today())
    lines = [
        InvoiceLine(invoice=invoice, line_type=InvoiceLine.LineType.SERVICE, description=service.name, quantity=Decimal("1.00"), unit_price=service.base_price, line_total=service.base_price)
        for service in job_card.services.all()
    ]
    lines.extend(
        InvoiceLine(invoice=invoice, line_type=InvoiceLine.LineType.PART, description=usage.part.name, quantity=usage.quantity, unit_price=usage.unit_sale_price, line_total=usage.quantity * usage.unit_sale_price)
        for usage in PartUsage.objects.filter(job_card=job_card).select_related("part")
    )
    InvoiceLine.objects.bulk_create(lines)
    return recalculate_invoice(invoice)


@transaction.atomic
def record_payment(invoice: Invoice, amount: Decimal, method: str, reference: str, recorded_by) -> Payment:
    if invoice.status == Invoice.Status.VOID:
        raise ValueError("لا يمكن تسجيل دفعة على فاتورة ملغاة.")
    remaining = invoice.total - invoice.amount_paid
    if amount > remaining:
        raise ValueError("لا يمكن أن تتجاوز الدفعة المبلغ المتبقي.")
    payment = Payment.objects.create(invoice=invoice, amount=amount, method=method, reference=reference, recorded_by=recorded_by)
    recalculate_invoice(invoice)
    return payment


def profit_and_loss(workshop, year: int, month: int):
    invoices = Invoice.objects.filter(workshop=workshop, issued_at__year=year, issued_at__month=month).exclude(status=Invoice.Status.VOID)
    revenue = invoices.aggregate(total=Sum("subtotal"))["total"] or Decimal("0.00")
    vat = invoices.aggregate(total=Sum("tax_amount"))["total"] or Decimal("0.00")
    expenses = Expense.objects.filter(workshop=workshop, occurred_at__year=year, occurred_at__month=month).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    invoice_job_ids = invoices.values_list("job_card_id", flat=True)
    parts_cost = sum((usage.quantity * usage.unit_purchase_price for usage in PartUsage.objects.filter(job_card_id__in=invoice_job_ids)), Decimal("0.00"))
    gross_profit = revenue - parts_cost
    net_profit = gross_profit - expenses
    return {"year": year, "month": month, "revenue": revenue, "vat": vat, "parts_cost": parts_cost, "expenses": expenses, "gross_profit": gross_profit, "net_profit": net_profit, "invoice_count": invoices.count()}
