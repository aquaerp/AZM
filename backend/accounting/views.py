from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import record_audit
from accounts.permissions import IsFinancialStaff, IsManagerOrAccountant
from workshop.models import JobCard

from .models import AccountingVoucher, Expense, Invoice, InvoiceLine
from .pdf import generate_invoice_pdf
from .serializers import AccountingVoucherSerializer, ExpenseSerializer, InvoiceLineSerializer, InvoiceSerializer, PaymentSerializer
from .services import create_invoice_from_job, profit_and_loss, recalculate_invoice, record_payment


class WorkshopAccountingQuerysetMixin:
    def get_queryset(self):
        return super().get_queryset().filter(workshop=self.request.user.workshop)


class InvoiceViewSet(WorkshopAccountingQuerysetMixin, viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("job_card__customer", "job_card__vehicle").prefetch_related("lines", "payments")
    serializer_class = InvoiceSerializer
    http_method_names = ("get", "patch", "head", "options", "post")

    def get_permissions(self):
        permission_class = IsManagerOrAccountant if self.action in ("list", "retrieve") else IsFinancialStaff
        return [permission_class()]

    def perform_update(self, serializer):
        invoice = serializer.save()
        recalculate_invoice(invoice)

    @action(detail=False, methods=("post",), url_path="create-from-job")
    def create_from_job(self, request):
        try:
            job = JobCard.objects.get(pk=request.data.get("job_card"), workshop=request.user.workshop)
            invoice = create_invoice_from_job(job)
        except JobCard.DoesNotExist:
            raise ValidationError({"job_card": "بطاقة العمل غير موجودة في ورشتك."})
        except ValueError as error:
            raise ValidationError({"job_card": str(error)})
        record_audit(request, "accounting.invoice_created", invoice, after={"invoice_number": invoice.invoice_number, "job_card_id": invoice.job_card_id, "total": invoice.total})
        return Response(self.get_serializer(invoice).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=("post",))
    def generate_pdf(self, request, *args, **kwargs):
        invoice = self.get_object()
        if invoice.status == Invoice.Status.VOID:
            raise ValidationError("لا يمكن توليد PDF لفاتورة ملغاة.")
        if invoice.status == Invoice.Status.DRAFT:
            invoice.status = Invoice.Status.ISSUED
            invoice.issued_at = timezone.now()
            invoice.save(update_fields=("status", "issued_at", "updated_at"))
        elif not invoice.issued_at:
            invoice.issued_at = timezone.now()
            invoice.save(update_fields=("issued_at", "updated_at"))
        language = "en" if request.headers.get("Accept-Language", "").lower().startswith("en") else "ar"
        generate_invoice_pdf(invoice, language=language)
        record_audit(request, "accounting.invoice_issued", invoice, after={"invoice_number": invoice.invoice_number, "status": invoice.status, "total": invoice.total})
        return Response(self.get_serializer(invoice).data)

    @action(detail=True, methods=("post",), url_path="record-payment")
    def record_payment(self, request, *args, **kwargs):
        invoice = self.get_object()
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = record_payment(
                invoice,
                amount=serializer.validated_data["amount"],
                method=serializer.validated_data.get("method", "cash"),
                reference=serializer.validated_data.get("reference", ""),
                recorded_by=request.user,
            )
        except ValueError as error:
            raise ValidationError({"amount": str(error)})
        invoice.refresh_from_db()
        job_card = invoice.job_card
        if invoice.status == Invoice.Status.PAID and job_card.status == JobCard.Status.READY and invoice.workshop.auto_deliver_paid_ready_jobs:
            now = timezone.now()
            job_card.status = JobCard.Status.DELIVERED
            job_card.delivered_at = now
            job_card.delivered_by = request.user
            job_card.delivery_method = "automatic"
            job_card.save(update_fields=("status", "delivered_at", "delivered_by", "delivery_method", "status_updated_at"))
            record_audit(request, "workshop.job_card_delivered", job_card, before={"status": JobCard.Status.READY}, after={"status": JobCard.Status.DELIVERED, "delivered_at": now, "delivery_method": "automatic"})
        if invoice.status == Invoice.Status.PAID:
            if not invoice.issued_at:
                invoice.issued_at = timezone.now()
                invoice.save(update_fields=("issued_at", "updated_at"))
            language = "en" if request.headers.get("Accept-Language", "").lower().startswith("en") else "ar"
            generate_invoice_pdf(invoice, language=language)
        record_audit(request, "accounting.payment_recorded", payment, entity_type="accounting.Payment", after={"invoice_id": invoice.id, "amount": payment.amount, "method": payment.method, "reference": payment.reference})
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class InvoiceLineViewSet(viewsets.ModelViewSet):
    queryset = InvoiceLine.objects.select_related("invoice")
    serializer_class = InvoiceLineSerializer
    permission_classes = (IsFinancialStaff,)

    def get_queryset(self):
        return super().get_queryset().filter(invoice__workshop=self.request.user.workshop)

    def perform_create(self, serializer):
        line = serializer.save()
        recalculate_invoice(line.invoice)

    def perform_update(self, serializer):
        line = serializer.save()
        recalculate_invoice(line.invoice)

    def perform_destroy(self, instance):
        invoice = instance.invoice
        if invoice.status != Invoice.Status.DRAFT:
            raise ValidationError("لا يمكن حذف بند من فاتورة صادرة أو مدفوعة.")
        instance.delete()
        recalculate_invoice(invoice)


class ExpenseViewSet(WorkshopAccountingQuerysetMixin, viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

    def get_permissions(self):
        permission_class = IsManagerOrAccountant if self.action in ("list", "retrieve") else IsFinancialStaff
        return [permission_class()]

    def perform_create(self, serializer):
        expense = serializer.save(workshop=self.request.user.workshop, created_by=self.request.user)
        record_audit(self.request, "accounting.expense_created", expense, after={"category": expense.category, "description": expense.description, "amount": expense.amount, "occurred_at": expense.occurred_at})

    def perform_update(self, serializer):
        expense = self.get_object()
        before = {"category": expense.category, "description": expense.description, "amount": expense.amount, "occurred_at": expense.occurred_at, "reference": expense.reference}
        expense = serializer.save()
        after = {"category": expense.category, "description": expense.description, "amount": expense.amount, "occurred_at": expense.occurred_at, "reference": expense.reference}
        record_audit(self.request, "accounting.expense_updated", expense, before=before, after=after)

    def perform_destroy(self, instance):
        before = {"category": instance.category, "description": instance.description, "amount": instance.amount, "occurred_at": instance.occurred_at, "reference": instance.reference}
        entity_id = instance.pk
        instance.delete()
        record_audit(self.request, "accounting.expense_deleted", entity_type="accounting.Expense", entity_id=entity_id, before=before)


class AccountingVoucherViewSet(WorkshopAccountingQuerysetMixin, viewsets.ModelViewSet):
    queryset = AccountingVoucher.objects.select_related("invoice", "payment", "expense")
    serializer_class = AccountingVoucherSerializer
    http_method_names = ("get", "head", "options", "post")

    def get_permissions(self):
        permission_class = IsManagerOrAccountant if self.action in ("list", "retrieve") else IsFinancialStaff
        return [permission_class()]

    def perform_create(self, serializer):
        voucher = serializer.save(workshop=self.request.user.workshop, created_by=self.request.user)
        record_audit(self.request, "accounting.voucher_created", voucher, after={"voucher_number": voucher.voucher_number, "voucher_type": voucher.voucher_type, "amount": voucher.amount, "invoice_id": voucher.invoice_id})


class ProfitLossView(APIView):
    permission_classes = (IsManagerOrAccountant,)

    def get(self, request):
        today = date.today()
        try:
            year = int(request.query_params.get("year", today.year))
            month = int(request.query_params.get("month", today.month))
            date(year, month, 1)
        except (TypeError, ValueError):
            raise ValidationError("أدخل سنة وشهراً صالحين.")
        return Response(profit_and_loss(request.user.workshop, year, month))
