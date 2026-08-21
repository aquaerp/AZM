from io import BytesIO

from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsManager, IsManagerOrAccountant
from accounts.audit import model_snapshot, record_audit

from .crypto import decrypt
from .models import Document, DocumentExpiryAlert
from .serializers import DocumentExpiryAlertSerializer, DocumentSerializer


class WorkshopDocumentQuerysetMixin:
    def get_queryset(self):
        return super().get_queryset().filter(workshop=self.request.user.workshop)


class DocumentViewSet(WorkshopDocumentQuerysetMixin, viewsets.ModelViewSet):
    queryset = Document.objects.select_related("customer", "vehicle", "employee__user")
    serializer_class = DocumentSerializer
    document_max_upload_bytes = settings.DOCUMENT_MAX_UPLOAD_BYTES

    def get_permissions(self):
        permission_class = IsManagerOrAccountant if self.action in ("list", "retrieve", "download", "expiring") else IsManager
        return [permission_class()]

    audit_fields = ("name", "document_type", "customer_id", "vehicle_id", "employee_id", "original_filename", "content_type", "expires_at")

    def perform_create(self, serializer):
        document = serializer.save()
        record_audit(self.request, "documents.document_uploaded", document, after=model_snapshot(document, self.audit_fields))

    def perform_update(self, serializer):
        document = self.get_object()
        before = model_snapshot(document, self.audit_fields)
        document = serializer.save()
        record_audit(self.request, "documents.document_updated", document, before=before, after=model_snapshot(document, self.audit_fields))

    def perform_destroy(self, instance):
        before = model_snapshot(instance, self.audit_fields)
        entity_id = instance.pk
        instance.delete()
        record_audit(self.request, "documents.document_deleted", entity_type="documents.Document", entity_id=entity_id, before=before)

    @action(detail=True, methods=("get",))
    def download(self, request, *args, **kwargs):
        document = self.get_object()
        with document.encrypted_file.open("rb") as stream:
            payload = decrypt(stream.read())
        return FileResponse(BytesIO(payload), as_attachment=True, filename=document.original_filename, content_type=document.content_type or "application/octet-stream")

    @action(detail=False, methods=("get",))
    def expiring(self, request):
        documents = self.get_queryset().filter(expires_at__isnull=False).order_by("expires_at")
        return Response(self.get_serializer(documents, many=True).data)


class DocumentExpiryAlertViewSet(WorkshopDocumentQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = DocumentExpiryAlert.objects.select_related("document")
    serializer_class = DocumentExpiryAlertSerializer
    permission_classes = (IsManager,)

    @action(detail=True, methods=("post",))
    def acknowledge(self, request, *args, **kwargs):
        alert = self.get_object()
        alert.acknowledged_at = timezone.now()
        alert.save(update_fields=("acknowledged_at",))
        record_audit(request, "documents.alert_acknowledged", alert, after={"document_id": alert.document_id, "days_before": alert.days_before, "acknowledged_at": alert.acknowledged_at})
        return Response(self.get_serializer(alert).data)
