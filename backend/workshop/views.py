from django.db.models import Count
from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from accounts.models import User
from accounts.audit import model_snapshot, record_audit
from accounts.permissions import IsManager, IsManagerOrAccountant, IsManagerOrTechnician, IsOperationalStaff, IsWorkshopReader

from .models import Customer, JobCard, Service, Vehicle
from .serializers import (
    CustomerSerializer,
    JobCardDetailSerializer,
    JobCardListSerializer,
    JobCardWriteSerializer,
    JobScheduleSerializer,
    JobStatusSerializer,
    PublicJobStatusSerializer,
    ServiceSerializer,
    VehicleSerializer,
)


class WorkshopQuerysetMixin:
    def get_queryset(self):
        return super().get_queryset().filter(workshop=self.request.user.workshop)


class ManagedWorkshopViewSet(WorkshopQuerysetMixin, viewsets.ModelViewSet):
    """Managers write operational records; accountants may read them."""

    def get_permissions(self):
        if self.action in ("portal_link", "rotate_portal_token"):
            return [IsManager()]
        permission_class = IsWorkshopReader if self.action in ("list", "retrieve") else IsOperationalStaff
        return [permission_class()]

    def perform_create(self, serializer):
        instance = serializer.save(workshop=self.request.user.workshop)
        record_audit(self.request, "workshop.record_created", instance, after=model_snapshot(instance, self.audit_fields))

    def perform_update(self, serializer):
        instance = self.get_object()
        before = model_snapshot(instance, self.audit_fields)
        instance = serializer.save()
        record_audit(self.request, "workshop.record_updated", instance, before=before, after=model_snapshot(instance, self.audit_fields))

    def perform_destroy(self, instance):
        before = model_snapshot(instance, self.audit_fields)
        entity_type = instance._meta.label
        entity_id = instance.pk
        instance.delete()
        record_audit(self.request, "workshop.record_deleted", entity_type=entity_type, entity_id=entity_id, before=before)


class CustomerViewSet(ManagedWorkshopViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    search_fields = ("name", "phone", "email")
    audit_fields = ("name", "phone", "email")


class VehicleViewSet(ManagedWorkshopViewSet):
    queryset = Vehicle.objects.select_related("customer")
    serializer_class = VehicleSerializer
    search_fields = ("license_plate", "vin", "make", "model", "customer__name")
    audit_fields = ("customer_id", "license_plate", "make", "model", "model_year", "vin")


class ServiceViewSet(ManagedWorkshopViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    search_fields = ("name",)
    audit_fields = ("name", "base_price", "is_active")


class JobCardViewSet(WorkshopQuerysetMixin, viewsets.ModelViewSet):
    queryset = JobCard.objects.select_related("customer", "vehicle").prefetch_related("services", "assigned_technicians")
    search_fields = ("job_number", "customer__name", "vehicle__license_plate")

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.TECHNICIAN:
            return queryset.filter(assigned_technicians=self.request.user)
        return queryset

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return JobCardWriteSerializer
        if self.action == "update_status":
            return JobStatusSerializer
        if self.action == "reschedule":
            return JobScheduleSerializer
        if self.action == "retrieve":
            return JobCardDetailSerializer
        return JobCardListSerializer

    def get_permissions(self):
        if self.action in ("portal_link", "rotate_portal_token"):
            return [IsManager()]
        if self.action in ("deliver", "reschedule"):
            return [IsOperationalStaff()]
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsOperationalStaff()]
        if self.action == "update_status":
            return [IsManagerOrTechnician()]
        return [IsWorkshopReader() if self.request.user.role != User.Role.TECHNICIAN else permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        job_card = serializer.save()
        record_audit(self.request, "workshop.job_card_created", job_card, after=model_snapshot(job_card, ("job_number", "customer_id", "vehicle_id", "status", "estimated_cost", "promised_at")))

    def perform_update(self, serializer):
        job_card = self.get_object()
        fields = ("customer_id", "vehicle_id", "status", "complaint", "diagnosis", "estimated_cost", "actual_cost", "promised_at")
        before = model_snapshot(job_card, fields)
        job_card = serializer.save()
        record_audit(self.request, "workshop.job_card_updated", job_card, before=before, after=model_snapshot(job_card, fields))

    def perform_destroy(self, instance):
        before = model_snapshot(instance, ("job_number", "customer_id", "vehicle_id", "status"))
        entity_id = instance.pk
        instance.delete()
        record_audit(self.request, "workshop.job_card_deleted", entity_type="workshop.JobCard", entity_id=entity_id, before=before)

    @action(detail=True, methods=("patch",), url_path="status")
    def update_status(self, request, *args, **kwargs):
        job_card = self.get_object()
        if request.data.get("status") == JobCard.Status.DELIVERED:
            raise PermissionDenied("استخدم إجراء التسليم المخصص بعد أن تصبح البطاقة جاهزة للتسليم.")
        if request.user.role == User.Role.TECHNICIAN:
            if not job_card.assigned_technicians.filter(pk=request.user.pk).exists():
                raise PermissionDenied("لا يمكنك تحديث بطاقة عمل غير مسندة إليك.")
            if request.data.get("status") not in (JobCard.Status.IN_PROGRESS, JobCard.Status.READY):
                raise PermissionDenied("يمكن للفني تغيير الحالة إلى قيد الإصلاح أو جاهزة فقط.")
            if set(request.data) - {"status", "diagnosis"}:
                raise PermissionDenied("لا يملك الفني صلاحية تعديل التكاليف المالية.")
        serializer = self.get_serializer(job_card, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        before = model_snapshot(job_card, ("status", "diagnosis", "actual_cost"))
        serializer.save()
        record_audit(request, "workshop.job_card_status_changed", job_card, before=before, after=model_snapshot(job_card, ("status", "diagnosis", "actual_cost")))
        return Response(JobCardDetailSerializer(job_card, context={"request": request}).data)

    @action(detail=True, methods=("patch",))
    def reschedule(self, request, *args, **kwargs):
        job_card = self.get_object()
        if job_card.status in (JobCard.Status.DELIVERED, JobCard.Status.CANCELLED):
            raise PermissionDenied("لا يمكن تغيير الموعد بعد تسليم البطاقة أو إلغائها.")
        serializer = self.get_serializer(job_card, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        before = {"promised_at": job_card.promised_at}
        serializer.save()
        record_audit(request, "workshop.job_card_rescheduled", job_card, before=before, after={"promised_at": job_card.promised_at})
        return Response(JobCardDetailSerializer(job_card, context={"request": request}).data)

    @action(detail=True, methods=("post",))
    def deliver(self, request, *args, **kwargs):
        job_card = self.get_object()
        if job_card.status != JobCard.Status.READY:
            raise PermissionDenied("لا يمكن تسليم البطاقة قبل أن يحولها الفني إلى جاهزة للتسليم.")
        now = timezone.now()
        before = {"status": job_card.status, "delivered_at": job_card.delivered_at}
        job_card.status = JobCard.Status.DELIVERED
        job_card.delivered_at = now
        job_card.delivered_by = request.user
        job_card.delivery_method = "manual"
        job_card.save(update_fields=("status", "delivered_at", "delivered_by", "delivery_method", "status_updated_at"))
        record_audit(request, "workshop.job_card_delivered", job_card, before=before, after={"status": job_card.status, "delivered_at": now, "delivery_method": "manual"})
        return Response(JobCardDetailSerializer(job_card, context={"request": request}).data)

    @action(detail=False, methods=("get",), url_path="dashboard")
    def dashboard(self, request):
        queryset = self.get_queryset()
        counts = {choice: 0 for choice, _label in JobCard.Status.choices}
        counts.update({row["status"]: row["count"] for row in queryset.values("status").annotate(count=Count("id"))})
        recent = queryset[:5]
        return Response({"counts": counts, "total": queryset.count(), "recent": JobCardListSerializer(recent, many=True, context={"request": request}).data})

    @action(detail=True, methods=("get",), url_path="portal-link")
    def portal_link(self, request, *args, **kwargs):
        job_card = self.get_object()
        return Response({"url": f"{settings.PORTAL_BASE_URL.rstrip('/')}/portal/{job_card.portal_token}"})

    @action(detail=True, methods=("post",), url_path="rotate-portal-token")
    def rotate_portal_token(self, request, *args, **kwargs):
        import uuid

        job_card = self.get_object()
        job_card.portal_token = uuid.uuid4()
        job_card.save(update_fields=("portal_token", "status_updated_at"))
        record_audit(request, "workshop.portal_token_rotated", job_card, after={"job_number": job_card.job_number})
        return Response({"url": f"{settings.PORTAL_BASE_URL.rstrip('/')}/portal/{job_card.portal_token}"})


class PublicJobStatusView(APIView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (AnonRateThrottle,)

    def get(self, request, token):
        try:
            job_card = JobCard.objects.select_related("vehicle").get(portal_token=token)
        except JobCard.DoesNotExist:
            raise NotFound("رابط متابعة الإصلاح غير صالح أو انتهت صلاحيته.")
        return Response(PublicJobStatusSerializer(job_card).data)
