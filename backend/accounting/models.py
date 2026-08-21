from decimal import Decimal
import uuid

from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Max

from accounts.models import Workshop
from workshop.models import JobCard, WorkshopOwnedModel


class Invoice(WorkshopOwnedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        ISSUED = "issued", "صادرة"
        PARTIAL = "partial", "مدفوعة جزئياً"
        PAID = "paid", "مدفوعة"
        VOID = "void", "ملغاة"

    job_card = models.OneToOneField(JobCard, on_delete=models.PROTECT, related_name="invoice")
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    sequence_number = models.PositiveBigIntegerField(editable=False)
    invoice_number = models.CharField(max_length=32, blank=True, editable=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    issued_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateField(null=True, blank=True)
    vat_rate = models.DecimalField("نسبة ضريبة القيمة المضافة", max_digits=5, decimal_places=2, default=Decimal("15.00"), validators=[MinValueValidator(Decimal("0.00"))])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to="invoices/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("workshop", "sequence_number"), name="unique_invoice_sequence_per_workshop"),
            models.UniqueConstraint(fields=("workshop", "invoice_number"), name="unique_invoice_number_per_workshop"),
        ]
        indexes = [models.Index(fields=("workshop", "status")), models.Index(fields=("workshop", "issued_at"))]
        verbose_name = "فاتورة"
        verbose_name_plural = "الفواتير"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.sequence_number:
            with transaction.atomic():
                Workshop.objects.select_for_update().get(pk=self.workshop_id)
                last = type(self).objects.filter(workshop_id=self.workshop_id).aggregate(value=Max("sequence_number"))["value"] or 0
                self.sequence_number = last + 1
                self.invoice_number = f"INV-{self.sequence_number:06d}"
                return super().save(*args, **kwargs)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number or "فاتورة جديدة"


class InvoiceLine(models.Model):
    class LineType(models.TextChoices):
        SERVICE = "service", "خدمة"
        PART = "part", "قطعة غيار"
        ADJUSTMENT = "adjustment", "تعديل"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    line_type = models.CharField(max_length=16, choices=LineType.choices)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"), validators=[MinValueValidator(Decimal("0.01"))])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    line_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    class Meta:
        ordering = ("id",)
        verbose_name = "بند فاتورة"
        verbose_name_plural = "بنود الفاتورة"

    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "نقدي"
        CARD = "card", "بطاقة"
        TRANSFER = "transfer", "تحويل"
        OTHER = "other", "أخرى"

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    method = models.CharField(max_length=16, choices=Method.choices, default=Method.CASH)
    reference = models.CharField(max_length=120, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="recorded_payments")

    class Meta:
        ordering = ("-paid_at",)
        verbose_name = "دفعة"
        verbose_name_plural = "الدفعات"


class Expense(WorkshopOwnedModel):
    class Category(models.TextChoices):
        RENT = "rent", "إيجار"
        SALARY = "salary", "رواتب"
        UTILITIES = "utilities", "خدمات ومرافق"
        SUPPLIES = "supplies", "مستلزمات"
        OTHER = "other", "أخرى"

    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    occurred_at = models.DateField()
    reference = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="created_expenses")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurred_at", "-created_at")
        indexes = [models.Index(fields=("workshop", "occurred_at")), models.Index(fields=("workshop", "category"))]
        verbose_name = "مصروف"
        verbose_name_plural = "المصروفات"


class AccountingVoucher(WorkshopOwnedModel):
    class VoucherType(models.TextChoices):
        RECEIPT = "receipt", "سند قبض"
        DISBURSEMENT = "disbursement", "سند صرف"

    voucher_number = models.CharField(max_length=24, unique=True, blank=True, editable=False)
    voucher_type = models.CharField(max_length=16, choices=VoucherType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    party_name = models.CharField(max_length=150)
    description = models.CharField(max_length=255)
    reference = models.CharField(max_length=120, blank=True)
    occurred_at = models.DateField()
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, null=True, blank=True, related_name="vouchers")
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, null=True, blank=True, related_name="voucher")
    expense = models.OneToOneField("Expense", on_delete=models.PROTECT, null=True, blank=True, related_name="voucher")
    created_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="created_vouchers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurred_at", "-created_at")
        indexes = [models.Index(fields=("workshop", "voucher_type", "occurred_at"))]
        verbose_name = "سند محاسبي"
        verbose_name_plural = "سندات محاسبية"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.voucher_number:
            prefix = "RCV" if self.voucher_type == self.VoucherType.RECEIPT else "DSB"
            self.voucher_number = f"{prefix}-{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(voucher_number=self.voucher_number)
