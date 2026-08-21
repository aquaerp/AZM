from datetime import date, timedelta

from cryptography.fernet import Fernet
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from accounts.models import AuditEvent, User, Workshop
from workshop.models import Customer

from . import crypto
from .models import Document, DocumentExpiryAlert
from .tasks import check_document_expirations


class DocumentApiTests(APITestCase):
    def setUp(self):
        self.workshop = Workshop.objects.create(name="ورشة عزم")
        self.other_workshop = Workshop.objects.create(name="ورشة أخرى")
        self.manager = User.objects.create_user(username="manager", password="SafePass123!", workshop=self.workshop, role=User.Role.MANAGER)
        self.customer = Customer.objects.create(workshop=self.workshop, name="خالد", phone="0500000000")
        self.other_customer = Customer.objects.create(workshop=self.other_workshop, name="عميل آخر", phone="0599999999")
        self.client.force_authenticate(self.manager)

    def test_upload_is_encrypted_and_download_restores_content(self):
        upload = SimpleUploadedFile("license.txt", b"private license data", content_type="text/plain")
        response = self.client.post("/api/documents/documents/", {"name": "رخصة", "document_type": "رخصة", "customer": self.customer.id, "file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document = Document.objects.get(name="رخصة")
        with document.encrypted_file.open("rb") as stream:
            self.assertNotEqual(stream.read(), b"private license data")
        response = self.client.get(f"/api/documents/documents/{document.id}/download/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), b"private license data")
        event = AuditEvent.objects.get(action="documents.document_uploaded")
        self.assertEqual(event.workshop, self.workshop)
        self.assertNotIn("encrypted_file", event.after)
        self.assertNotIn("private license data", str(event.after))

    def test_rejects_document_owner_from_another_workshop(self):
        upload = SimpleUploadedFile("doc.txt", b"content", content_type="text/plain")
        response = self.client.post("/api/documents/documents/", {"name": "مرفق", "document_type": "عقد", "customer": self.other_customer.id, "file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_daily_task_creates_45_day_alert_once(self):
        document = Document.objects.create(workshop=self.workshop, name="شهادة", document_type="شهادة", original_filename="certificate.txt", content_type="text/plain", encrypted_file=SimpleUploadedFile("certificate.enc", b"encrypted"), expires_at=date.today() + timedelta(days=45), uploaded_by=self.manager)

        first = check_document_expirations()
        second = check_document_expirations()

        self.assertEqual(first, 1)
        self.assertEqual(second, 0)
        self.assertTrue(DocumentExpiryAlert.objects.filter(document=document, days_before=45).exists())

    def test_manager_cannot_retrieve_or_download_other_workshop_document(self):
        other_manager = User.objects.create_user(username="other-doc-manager", password="SafePass123!", workshop=self.other_workshop, role=User.Role.MANAGER)
        document = Document.objects.create(
            workshop=self.other_workshop,
            name="Private",
            document_type="Contract",
            original_filename="private.txt",
            content_type="text/plain",
            encrypted_file=SimpleUploadedFile("private.enc", crypto.encrypt(b"other workshop secret")),
            uploaded_by=other_manager,
        )

        self.assertEqual(self.client.get(f"/api/documents/documents/{document.id}/").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(f"/api/documents/documents/{document.id}/download/").status_code, status.HTTP_404_NOT_FOUND)

    def test_document_alert_list_and_acknowledge_are_workshop_scoped(self):
        own_document = Document.objects.create(workshop=self.workshop, name="Own", document_type="Contract", original_filename="own.txt", content_type="text/plain", encrypted_file=SimpleUploadedFile("own.enc", crypto.encrypt(b"own")), uploaded_by=self.manager)
        other_manager = User.objects.create_user(username="other-alert-manager", password="SafePass123!", workshop=self.other_workshop, role=User.Role.MANAGER)
        other_document = Document.objects.create(workshop=self.other_workshop, name="Other", document_type="Contract", original_filename="other.txt", content_type="text/plain", encrypted_file=SimpleUploadedFile("other.enc", crypto.encrypt(b"other")), uploaded_by=other_manager)
        own_alert = DocumentExpiryAlert.objects.create(workshop=self.workshop, document=own_document, days_before=30)
        other_alert = DocumentExpiryAlert.objects.create(workshop=self.other_workshop, document=other_document, days_before=30)

        response = self.client.get("/api/documents/alerts/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [own_alert.id])
        self.assertEqual(self.client.post(f"/api/documents/alerts/{other_alert.id}/acknowledge/").status_code, status.HTTP_404_NOT_FOUND)
        other_alert.refresh_from_db()
        self.assertIsNone(other_alert.acknowledged_at)
        self.client.post(f"/api/documents/alerts/{own_alert.id}/acknowledge/")
        self.assertTrue(AuditEvent.objects.filter(action="documents.alert_acknowledged", workshop=self.workshop, entity_id=str(own_alert.id)).exists())
