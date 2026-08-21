from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import CanIssueParts, CanManageInventory, CanReviewPartRequests, IsInventoryReader
from accounts.audit import model_snapshot, record_audit

from .models import InventoryAlert, Part, PartRequest, PartUsage, Supplier
from .serializers import InventoryAlertSerializer, PartRequestSerializer, PartSerializer, PartUsageSerializer, SupplierSerializer
from .services import sync_low_stock_alert


class WorkshopInventoryQuerysetMixin:
    def get_queryset(self):
        return super().get_queryset().filter(workshop=self.request.user.workshop)


class ManagedInventoryViewSet(WorkshopInventoryQuerysetMixin, viewsets.ModelViewSet):
    def get_permissions(self):
        permission_class = IsInventoryReader if self.action in ("list", "retrieve", "low_stock") else CanManageInventory
        return [permission_class()]

    def perform_create(self, serializer):
        part = serializer.save(workshop=self.request.user.workshop)
        record_audit(self.request, "inventory.record_created", part, after=model_snapshot(part, self.audit_fields))
        if isinstance(part, Part):
            sync_low_stock_alert(part)

    def perform_update(self, serializer):
        current = self.get_object()
        before = model_snapshot(current, self.audit_fields)
        part = serializer.save()
        record_audit(self.request, "inventory.record_updated", part, before=before, after=model_snapshot(part, self.audit_fields))
        if isinstance(part, Part):
            sync_low_stock_alert(part)

    def perform_destroy(self, instance):
        before = model_snapshot(instance, self.audit_fields)
        entity_type = instance._meta.label
        entity_id = instance.pk
        instance.delete()
        record_audit(self.request, "inventory.record_deleted", entity_type=entity_type, entity_id=entity_id, before=before)


class SupplierViewSet(ManagedInventoryViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    search_fields = ("name", "phone", "contact_name")
    audit_fields = ("name", "contact_name", "phone", "email", "is_active")


class PartViewSet(ManagedInventoryViewSet):
    queryset = Part.objects.select_related("supplier")
    serializer_class = PartSerializer
    search_fields = ("name", "sku")
    audit_fields = ("name", "sku", "supplier_id", "quantity", "reorder_level", "purchase_price", "sale_price", "is_active")

    @action(detail=False, methods=("get",), url_path="low-stock")
    def low_stock(self, request):
        parts = self.get_queryset().filter(is_active=True, quantity__lte=F("reorder_level"))
        return Response(PartSerializer(parts, many=True, context={"request": request}).data)


class PartUsageViewSet(WorkshopInventoryQuerysetMixin, viewsets.ModelViewSet):
    queryset = PartUsage.objects.select_related("part", "job_card")
    serializer_class = PartUsageSerializer
    http_method_names = ("get", "post", "delete", "head", "options")

    def get_permissions(self):
        permission_class = IsInventoryReader if self.action in ("list", "retrieve") else CanIssueParts
        return [permission_class()]

    def perform_create(self, serializer):
        usage = serializer.save()
        record_audit(self.request, "inventory.part_issued", usage, after=model_snapshot(usage, ("job_card_id", "part_id", "quantity", "unit_purchase_price", "unit_sale_price")))

    def perform_destroy(self, instance):
        before = model_snapshot(instance, ("job_card_id", "part_id", "quantity", "unit_purchase_price", "unit_sale_price"))
        entity_id = instance.pk
        with transaction.atomic():
            part = Part.objects.select_for_update().select_related("workshop").get(pk=instance.part_id)
            part.quantity += instance.quantity
            part.save(update_fields=("quantity", "updated_at"))
            instance.delete()
            sync_low_stock_alert(part)
        record_audit(self.request, "inventory.part_issue_reversed", entity_type="inventory.PartUsage", entity_id=entity_id, before=before)


class InventoryAlertViewSet(WorkshopInventoryQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = InventoryAlert.objects.select_related("part")
    serializer_class = InventoryAlertSerializer
    permission_classes = (CanManageInventory,)

    @action(detail=True, methods=("post",))
    def acknowledge(self, request, *args, **kwargs):
        alert = self.get_object()
        alert.acknowledged_at = timezone.now()
        alert.save(update_fields=("acknowledged_at", "updated_at"))
        record_audit(request, "inventory.alert_acknowledged", alert, after={"part_id": alert.part_id, "acknowledged_at": alert.acknowledged_at})
        return Response(self.get_serializer(alert).data)


class PartRequestViewSet(WorkshopInventoryQuerysetMixin, viewsets.ModelViewSet):
    queryset = PartRequest.objects.select_related("part", "job_card", "requested_by", "reviewed_by", "fulfilled_usage")
    serializer_class = PartRequestSerializer
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.TECHNICIAN:
            return queryset.filter(requested_by=self.request.user)
        return queryset

    def get_permissions(self):
        if self.action == "create":
            return [IsInventoryReader()]
        if self.action in ("approve", "reject", "fulfill"):
            return [CanReviewPartRequests()]
        return [IsInventoryReader()]

    def perform_create(self, serializer):
        part_request = serializer.save(workshop=self.request.user.workshop, requested_by=self.request.user)
        record_audit(self.request, "inventory.part_requested", part_request, after=model_snapshot(part_request, ("job_card_id", "part_id", "quantity", "status")))

    def _review(self, part_request, target_status):
        if part_request.status not in (PartRequest.Status.REQUESTED, PartRequest.Status.APPROVED):
            raise ValidationError("تمت معالجة طلب القطعة بالفعل.")
        part_request.status = target_status
        part_request.reviewed_by = self.request.user
        part_request.reviewed_at = timezone.now()
        part_request.save(update_fields=("status", "reviewed_by", "reviewed_at"))
        return part_request

    @action(detail=True, methods=("post",))
    def approve(self, request, *args, **kwargs):
        part_request = self._review(self.get_object(), PartRequest.Status.APPROVED)
        record_audit(request, "inventory.part_request_approved", part_request, after={"status": part_request.status})
        return Response(self.get_serializer(part_request).data)

    @action(detail=True, methods=("post",))
    def reject(self, request, *args, **kwargs):
        part_request = self._review(self.get_object(), PartRequest.Status.REJECTED)
        record_audit(request, "inventory.part_request_rejected", part_request, after={"status": part_request.status})
        return Response(self.get_serializer(part_request).data)

    @action(detail=True, methods=("post",))
    def fulfill(self, request, *args, **kwargs):
        part_request = self.get_object()
        if part_request.status not in (PartRequest.Status.REQUESTED, PartRequest.Status.APPROVED):
            raise ValidationError("لا يمكن صرف طلب تمت معالجته سابقًا.")
        usage_serializer = PartUsageSerializer(data={"job_card": part_request.job_card_id, "part": part_request.part_id, "quantity": part_request.quantity}, context={"request": request})
        usage_serializer.is_valid(raise_exception=True)
        usage = usage_serializer.save()
        part_request.status = PartRequest.Status.FULFILLED
        part_request.reviewed_by = request.user
        part_request.reviewed_at = timezone.now()
        part_request.fulfilled_usage = usage
        part_request.save(update_fields=("status", "reviewed_by", "reviewed_at", "fulfilled_usage"))
        record_audit(request, "inventory.part_request_fulfilled", part_request, after={"status": part_request.status, "part_usage_id": usage.id})
        return Response(self.get_serializer(part_request).data)
