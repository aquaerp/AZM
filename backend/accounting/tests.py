from datetime import date
from decimal import Decimal
import base64

from rest_framework import status
from rest_framework.test import APITestCase
from django.test import SimpleTestCase
from django.utils import timezone

from accounts.models import User, Workshop
from accounts.models import AuditEvent
from inventory.models import Part, PartUsage
from workshop.models import Customer, JobCard, Service, Vehicle

from .models import AccountingVoucher, Expense, Invoice, InvoiceLine, Payment
from .services import recalculate_invoice
from .zatca import encode_tlv


class ZatcaTlvTests(SimpleTestCase):
    def test_tlv_uses_utf8_byte_lengths_and_base64_round_trip(self):
        fields = ((1, "ورشة عزم"), (2, "310123456789003"), (3, "2026-08-11T12:30:00+03:00"), (4, "115.00"), (5, "15.00"))

        encoded = encode_tlv(fields)
        decoded = base64.b64decode(base64.b64encode(encoded))

        self.assertEqual(decoded, encoded)
        self.assertEqual(decoded[0], 1)
        self.assertEqual(decoded[1], len("ورشة عزم".encode("utf-8")))


class AccountingApiTests(APITestCase):
    def setUp(self):
        self.workshop = Workshop.objects.create(name="ورشة عزم", legal_name="ورشة عزم للسيارات", tax_number="310123456789003")
        self.other_workshop = Workshop.objects.create(name="ورشة أخرى", legal_name="ورشة أخرى للسيارات", tax_number="310999999999003")
        self.manager = User.objects.create_user(username="manager", password="SafePass123!", workshop=self.workshop, role=User.Role.MANAGER)
        customer = Customer.objects.create(workshop=self.workshop, name="خالد", phone="0500000000")
        vehicle = Vehicle.objects.create(workshop=self.workshop, customer=customer, license_plate="أ ب ج 123", make="Toyota", model="Camry")
        self.job = JobCard.objects.create(workshop=self.workshop, customer=customer, vehicle=vehicle, complaint="صيانة", status=JobCard.Status.READY, created_by=self.manager)
        service = Service.objects.create(workshop=self.workshop, name="تغيير زيت", base_price="100.00")
        self.job.services.add(service)
        part = Part.objects.create(workshop=self.workshop, name="فلتر", sku="F-1", quantity=3, reorder_level=1, purchase_price="10.00", sale_price="20.00")
        PartUsage.objects.create(workshop=self.workshop, job_card=self.job, part=part, quantity=1, unit_purchase_price="10.00", unit_sale_price="20.00", added_by=self.manager)
        self.client.force_authenticate(self.manager)

        other_manager = User.objects.create_user(username="other-manager", password="SafePass123!", workshop=self.other_workshop, role=User.Role.MANAGER)
        other_customer = Customer.objects.create(workshop=self.other_workshop, name="عميل آخر", phone="0599999999")
        other_vehicle = Vehicle.objects.create(workshop=self.other_workshop, customer=other_customer, license_plate="OTHER-1", make="Kia", model="K5")
        other_job = JobCard.objects.create(workshop=self.other_workshop, customer=other_customer, vehicle=other_vehicle, complaint="Other", status=JobCard.Status.READY, created_by=other_manager)
        self.other_invoice = Invoice.objects.create(workshop=self.other_workshop, job_card=other_job, status=Invoice.Status.ISSUED, issued_at=timezone.now(), subtotal="100.00", tax_amount="15.00", total="115.00")

    def test_create_invoice_from_ready_job(self):
        response = self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invoice = Invoice.objects.get(job_card=self.job)
        self.assertEqual(invoice.subtotal, Decimal("120.00"))
        self.assertEqual(invoice.tax_amount, Decimal("18.00"))
        self.assertEqual(invoice.total, Decimal("138.00"))
        self.assertEqual(invoice.sequence_number, 1)
        self.assertEqual(invoice.invoice_number, "INV-000001")
        self.assertEqual(self.other_invoice.sequence_number, 1)
        self.assertEqual(self.other_invoice.invoice_number, "INV-000001")
        self.assertNotEqual(invoice.uuid, self.other_invoice.uuid)

    def test_payment_changes_invoice_status(self):
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)
        response = self.client.post(f"/api/accounting/invoices/{invoice.id}/record-payment/", {"amount": "40.00", "method": "cash"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PARTIAL)
        self.assertEqual(invoice.amount_paid, Decimal("40.00"))

    def test_point_of_sale_card_payment_keeps_method_and_reference(self):
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)

        response = self.client.post(
            f"/api/accounting/invoices/{invoice.id}/record-payment/",
            {"amount": "138.00", "method": "card", "reference": "POS-TEST-001"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payment = Payment.objects.get(invoice=invoice)
        self.assertEqual(payment.method, Payment.Method.CARD)
        self.assertEqual(payment.reference, "POS-TEST-001")
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)

    def test_receipt_voucher_records_payment_and_updates_invoice(self):
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)
        invoice.status = Invoice.Status.ISSUED
        invoice.issued_at = timezone.now()
        invoice.save(update_fields=("status", "issued_at", "updated_at"))

        response = self.client.post("/api/accounting/vouchers/", {"voucher_type": "receipt", "invoice": invoice.id, "amount": "40.00", "party_name": "Customer", "description": "Receipt voucher", "reference": "RCV-REF", "occurred_at": str(date.today()), "payment_method": "cash"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        voucher = AccountingVoucher.objects.get(voucher_type=AccountingVoucher.VoucherType.RECEIPT)
        self.assertTrue(voucher.voucher_number.startswith("RCV-"))
        self.assertEqual(voucher.payment.amount, Decimal("40.00"))
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount_paid, Decimal("40.00"))

    def test_disbursement_voucher_creates_expense(self):
        response = self.client.post("/api/accounting/vouchers/", {"voucher_type": "disbursement", "amount": "30.00", "party_name": "Supplier", "description": "Workshop supplies", "reference": "DSB-REF", "occurred_at": str(date.today()), "category": "supplies"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        voucher = AccountingVoucher.objects.get(voucher_type=AccountingVoucher.VoucherType.DISBURSEMENT)
        self.assertTrue(voucher.voucher_number.startswith("DSB-"))
        self.assertEqual(voucher.expense.amount, Decimal("30.00"))
        self.assertEqual(voucher.expense.category, "supplies")

    def test_receipt_voucher_rejects_amount_above_invoice_balance(self):
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)
        invoice.status = Invoice.Status.ISSUED
        invoice.issued_at = timezone.now()
        invoice.save(update_fields=("status", "issued_at", "updated_at"))

        response = self.client.post("/api/accounting/vouchers/", {"voucher_type": "receipt", "invoice": invoice.id, "amount": "9999.00", "party_name": "Customer", "description": "Invalid receipt", "occurred_at": str(date.today())})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AccountingVoucher.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)

    def test_expense_and_profit_loss_report(self):
        invoice = Invoice.objects.create(workshop=self.workshop, job_card=self.job, status=Invoice.Status.ISSUED, issued_at=timezone.now(), subtotal="120.00", tax_amount="18.00", total="138.00")
        Expense.objects.create(workshop=self.workshop, category="rent", description="إيجار", amount="30.00", occurred_at=date.today(), created_by=self.manager)

        response = self.client.get(f"/api/accounting/reports/profit-loss/?year={date.today().year}&month={date.today().month}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["revenue"]), Decimal("120.00"))
        self.assertEqual(Decimal(response.data["parts_cost"]), Decimal("10.00"))
        self.assertEqual(Decimal(response.data["net_profit"]), Decimal("80.00"))

    def test_generate_pdf_for_invoice(self):
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)

        response = self.client.post(f"/api/accounting/invoices/{invoice.id}/generate_pdf/", HTTP_ACCEPT_LANGUAGE="en")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invoice.refresh_from_db()
        self.assertTrue(invoice.pdf_file.name.endswith(".pdf"))
        with invoice.pdf_file.open("rb") as pdf:
            self.assertEqual(pdf.read(4), b"%PDF")

    def test_draft_invoice_lines_and_vat_can_be_corrected(self):
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)
        line = invoice.lines.get(line_type=InvoiceLine.LineType.SERVICE)

        line_response = self.client.patch(f"/api/accounting/invoice-lines/{line.id}/", {"quantity": "2.00", "unit_price": "75.00", "description": "خدمة مصححة"})
        invoice_response = self.client.patch(f"/api/accounting/invoices/{invoice.id}/", {"vat_rate": "10.00", "notes": "تم تصحيح القيمة"})

        self.assertEqual(line_response.status_code, status.HTTP_200_OK)
        self.assertEqual(invoice_response.status_code, status.HTTP_200_OK)
        invoice.refresh_from_db()
        line.refresh_from_db()
        self.assertEqual(line.line_total, Decimal("150.00"))
        self.assertEqual(invoice.subtotal, Decimal("170.00"))
        self.assertEqual(invoice.tax_amount, Decimal("17.00"))
        self.assertEqual(invoice.total, Decimal("187.00"))

    def test_issued_invoice_lines_cannot_be_changed_or_deleted(self):
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)
        line = invoice.lines.first()
        invoice.status = Invoice.Status.ISSUED
        invoice.issued_at = timezone.now()
        invoice.save(update_fields=("status", "issued_at", "updated_at"))

        changed = self.client.patch(f"/api/accounting/invoice-lines/{line.id}/", {"unit_price": "1.00"})
        deleted = self.client.delete(f"/api/accounting/invoice-lines/{line.id}/")
        metadata = self.client.patch(f"/api/accounting/invoices/{invoice.id}/", {"vat_rate": "1.00"})

        self.assertEqual(changed.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(deleted.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(metadata.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_arabic_multi_page_pdf_without_dropping_lines(self):
        self.workshop.legal_name = "ورشة عزم للسيارات"
        self.workshop.tax_number = "310123456789003"
        self.workshop.commercial_registration = "1010123456"
        self.workshop.national_address = "الرياض، المملكة العربية السعودية"
        self.workshop.save()
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)
        InvoiceLine.objects.bulk_create([
            InvoiceLine(invoice=invoice, line_type=InvoiceLine.LineType.SERVICE, description=f"خدمة إضافية رقم {index}", quantity=1, unit_price="5.00", line_total="5.00")
            for index in range(45)
        ])
        recalculate_invoice(invoice)

        response = self.client.post(f"/api/accounting/invoices/{invoice.id}/generate_pdf/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invoice.refresh_from_db()
        with invoice.pdf_file.open("rb") as pdf:
            payload = pdf.read()
        self.assertEqual(payload[:4], b"%PDF")
        self.assertGreaterEqual(payload.count(b"/Type /Page"), 2)

    def test_manager_cannot_access_or_pay_other_workshop_invoice(self):
        url = f"/api/accounting/invoices/{self.other_invoice.id}/"

        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        payment = self.client.post(f"{url}record-payment/", {"amount": "10.00", "method": "cash"})
        self.assertEqual(payment.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Payment.objects.filter(invoice=self.other_invoice).exists())

    def test_profit_loss_report_excludes_other_workshop_finances(self):
        Expense.objects.create(workshop=self.other_workshop, category="rent", description="Other expense", amount="9999.00", occurred_at=date.today(), created_by=self.other_invoice.job_card.created_by)

        response = self.client.get(f"/api/accounting/reports/profit-loss/?year={date.today().year}&month={date.today().month}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["revenue"]), Decimal("0.00"))
        self.assertEqual(Decimal(response.data["expenses"]), Decimal("0.00"))
        self.assertEqual(response.data["invoice_count"], 0)

    def test_accountant_can_record_expense_and_payment(self):
        accountant = User.objects.create_user(username="accountant", password="SafePass123!", workshop=self.workshop, role=User.Role.ACCOUNTANT)
        self.client.force_authenticate(accountant)
        expense = self.client.post("/api/accounting/expenses/", {"category": "supplies", "description": "Office", "amount": "25.00", "occurred_at": str(date.today())})
        self.client.force_authenticate(self.manager)
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)
        self.client.force_authenticate(accountant)

        payment = self.client.post(f"/api/accounting/invoices/{invoice.id}/record-payment/", {"amount": "10.00", "method": "cash"})

        self.assertEqual(expense.status_code, status.HTTP_201_CREATED)
        self.assertEqual(payment.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Expense.objects.filter(workshop=self.workshop, created_by=accountant, amount="25.00").exists())
        self.assertTrue(AuditEvent.objects.filter(workshop=self.workshop, actor=accountant, action="accounting.expense_created").exists())
        self.assertTrue(AuditEvent.objects.filter(workshop=self.workshop, actor=accountant, action="accounting.payment_recorded").exists())

    def test_full_payment_generates_pdf_and_optionally_delivers_ready_job(self):
        self.workshop.auto_deliver_paid_ready_jobs = True
        self.workshop.save(update_fields=("auto_deliver_paid_ready_jobs",))
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)

        response = self.client.post(f"/api/accounting/invoices/{invoice.id}/record-payment/", {"amount": str(invoice.total), "method": "card"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invoice.refresh_from_db()
        self.job.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertTrue(invoice.pdf_file.name.endswith(".pdf"))
        self.assertEqual(self.job.status, JobCard.Status.DELIVERED)
        self.assertEqual(self.job.delivery_method, "automatic")

    def test_paid_invoice_pdf_can_be_generated_without_tax_number(self):
        self.workshop.tax_number = ""
        self.workshop.save(update_fields=("tax_number",))
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)
        self.client.post(f"/api/accounting/invoices/{invoice.id}/record-payment/", {"amount": str(invoice.total), "method": "cash"})

        response = self.client.post(f"/api/accounting/invoices/{invoice.id}/generate_pdf/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invoice.refresh_from_db()
        self.assertTrue(invoice.pdf_file.name.endswith(".pdf"))

    def test_generated_pdf_download_is_authenticated_and_returns_pdf(self):
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)
        self.client.post(f"/api/accounting/invoices/{invoice.id}/generate_pdf/")

        response = self.client.get(f"/api/accounting/invoices/{invoice.id}/download-pdf/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(f'filename="{invoice.invoice_number}.pdf"', response["Content-Disposition"])
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF"))

        self.client.force_authenticate(user=None)
        unauthorized = self.client.get(f"/api/accounting/invoices/{invoice.id}/download-pdf/")
        self.assertEqual(unauthorized.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pdf_for_legacy_paid_invoice_sets_missing_issue_date(self):
        self.client.post("/api/accounting/invoices/create-from-job/", {"job_card": self.job.id})
        invoice = Invoice.objects.get(job_card=self.job)
        Payment.objects.create(invoice=invoice, amount=invoice.total, method=Payment.Method.CASH, recorded_by=self.manager)
        recalculate_invoice(invoice)
        invoice.refresh_from_db()
        self.assertIsNone(invoice.issued_at)

        response = self.client.post(f"/api/accounting/invoices/{invoice.id}/generate_pdf/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invoice.refresh_from_db()
        self.assertIsNotNone(invoice.issued_at)
        self.assertTrue(invoice.pdf_file.name.endswith(".pdf"))
