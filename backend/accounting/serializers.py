from decimal import Decimal

from rest_framework import serializers

from .models import AccountingVoucher, Expense, Invoice, InvoiceLine, Payment
from .services import record_payment


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = ("id", "invoice", "line_type", "description", "quantity", "unit_price", "line_total")
        read_only_fields = ("id", "line_total")

    def validate_invoice(self, invoice):
        if invoice.workshop_id != self.context["request"].user.workshop_id:
            raise serializers.ValidationError("الفاتورة لا تنتمي إلى ورشتك.")
        if invoice.status != Invoice.Status.DRAFT:
            raise serializers.ValidationError("لا يمكن تعديل بنود فاتورة صادرة أو مدفوعة.")
        return invoice

    def validate(self, attributes):
        invoice = attributes.get("invoice") or getattr(self.instance, "invoice", None)
        if invoice:
            if invoice.workshop_id != self.context["request"].user.workshop_id:
                raise serializers.ValidationError({"invoice": "الفاتورة لا تنتمي إلى ورشتك."})
            if invoice.status != Invoice.Status.DRAFT:
                raise serializers.ValidationError("لا يمكن تعديل بنود فاتورة صادرة أو مدفوعة.")
        return attributes


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "amount", "method", "reference", "paid_at")
        read_only_fields = ("id", "paid_at")


class InvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="job_card.customer.name", read_only=True)
    vehicle_label = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    pdf_url = serializers.SerializerMethodField()
    lines = InvoiceLineSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = ("id", "job_card", "invoice_number", "customer_name", "vehicle_label", "status", "status_label", "issued_at", "due_at", "vat_rate", "subtotal", "tax_amount", "total", "amount_paid", "notes", "pdf_url", "lines", "payments", "created_at")
        read_only_fields = ("id", "job_card", "invoice_number", "customer_name", "vehicle_label", "status", "status_label", "subtotal", "tax_amount", "total", "amount_paid", "pdf_url", "lines", "payments", "created_at")

    def get_vehicle_label(self, instance):
        vehicle = instance.job_card.vehicle
        return f"{vehicle.make} {vehicle.model} — {vehicle.license_plate}"

    def get_pdf_url(self, instance):
        if not instance.pdf_file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(instance.pdf_file.url) if request else instance.pdf_file.url

    def validate(self, attributes):
        if self.instance and self.instance.status != Invoice.Status.DRAFT:
            raise serializers.ValidationError("لا يمكن تعديل فاتورة صادرة أو مدفوعة.")
        return attributes


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ("id", "category", "description", "amount", "occurred_at", "reference", "created_at")
        read_only_fields = ("id", "created_at")


class AccountingVoucherSerializer(serializers.ModelSerializer):
    voucher_type_label = serializers.CharField(source="get_voucher_type_display", read_only=True)
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True)
    payment_method = serializers.ChoiceField(choices=Payment.Method.choices, write_only=True, required=False, default=Payment.Method.CASH)
    category = serializers.ChoiceField(choices=Expense.Category.choices, write_only=True, required=False, default=Expense.Category.OTHER)

    class Meta:
        model = AccountingVoucher
        fields = ("id", "voucher_number", "voucher_type", "voucher_type_label", "amount", "party_name", "description", "reference", "occurred_at", "invoice", "invoice_number", "payment_method", "category", "payment", "expense", "created_at")
        read_only_fields = ("id", "voucher_number", "voucher_type_label", "invoice_number", "payment", "expense", "created_at")

    def validate(self, attributes):
        request = self.context["request"]
        voucher_type = attributes.get("voucher_type")
        invoice = attributes.get("invoice")
        if voucher_type == AccountingVoucher.VoucherType.RECEIPT:
            if not invoice:
                raise serializers.ValidationError({"invoice": "اختر فاتورة لسند القبض."})
            if invoice.workshop_id != request.user.workshop_id:
                raise serializers.ValidationError({"invoice": "الفاتورة لا تنتمي إلى ورشتك."})
            if invoice.status in (Invoice.Status.DRAFT, Invoice.Status.VOID, Invoice.Status.PAID):
                raise serializers.ValidationError({"invoice": "لا يمكن إنشاء سند قبض لهذه الفاتورة."})
        elif voucher_type == AccountingVoucher.VoucherType.DISBURSEMENT:
            attributes["invoice"] = None
        return attributes

    def create(self, validated_data):
        payment_method = validated_data.pop("payment_method", Payment.Method.CASH)
        category = validated_data.pop("category", Expense.Category.OTHER)
        voucher_type = validated_data["voucher_type"]
        workshop = validated_data.pop("workshop")
        created_by = validated_data.pop("created_by")
        if voucher_type == AccountingVoucher.VoucherType.RECEIPT:
            try:
                payment = record_payment(validated_data["invoice"], validated_data["amount"], payment_method, validated_data.get("reference", ""), created_by)
            except ValueError as error:
                raise serializers.ValidationError({"amount": str(error)}) from error
            return AccountingVoucher.objects.create(workshop=workshop, created_by=created_by, payment=payment, **validated_data)
        expense = Expense.objects.create(workshop=workshop, created_by=created_by, category=category, description=validated_data["description"], amount=validated_data["amount"], occurred_at=validated_data["occurred_at"], reference=validated_data.get("reference", ""))
        return AccountingVoucher.objects.create(workshop=workshop, created_by=created_by, expense=expense, **validated_data)
