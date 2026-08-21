from django.contrib import admin

from .models import AccountingVoucher, Expense, Invoice, InvoiceLine, Payment


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("paid_at",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "job_card", "status", "total", "amount_paid", "workshop")
    list_filter = ("workshop", "status")
    search_fields = ("invoice_number", "job_card__job_number")
    inlines = (InvoiceLineInline, PaymentInline)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("description", "category", "amount", "occurred_at", "workshop")
    list_filter = ("workshop", "category")
    search_fields = ("description", "reference")


@admin.register(AccountingVoucher)
class AccountingVoucherAdmin(admin.ModelAdmin):
    list_display = ("voucher_number", "voucher_type", "amount", "party_name", "occurred_at", "workshop")
    list_filter = ("workshop", "voucher_type")
    search_fields = ("voucher_number", "party_name", "reference")
