from datetime import date

from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import IsManager, IsManagerOrAccountant, IsManagerOrTechnician, IsWorkshopTeamMember

from .models import Employee, EmployeeCommission, JobTask
from .serializers import EmployeeCommissionSerializer, EmployeeSerializer, JobTaskSerializer
from .services import generate_monthly_commissions


class WorkshopWorkforceQuerysetMixin:
    def get_queryset(self):
        return super().get_queryset().filter(workshop=self.request.user.workshop)


class EmployeeViewSet(WorkshopWorkforceQuerysetMixin, viewsets.ModelViewSet):
    queryset = Employee.objects.select_related("user")
    serializer_class = EmployeeSerializer

    def get_permissions(self):
        permission_class = IsManagerOrAccountant if self.action in ("list", "retrieve") else IsManager
        return [permission_class()]

    def perform_create(self, serializer):
        serializer.save(workshop=self.request.user.workshop)


class JobTaskViewSet(WorkshopWorkforceQuerysetMixin, viewsets.ModelViewSet):
    queryset = JobTask.objects.select_related("employee__user", "job_card")
    serializer_class = JobTaskSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.TECHNICIAN:
            return queryset.filter(employee__user=self.request.user)
        return queryset

    def get_permissions(self):
        if self.action in ("start", "complete"):
            return [IsManagerOrTechnician()]
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsManager()]
        return [IsWorkshopTeamMember()]

    def perform_create(self, serializer):
        task = serializer.save(workshop=self.request.user.workshop)
        task.job_card.assigned_technicians.add(task.employee.user)

    def _assert_task_actor(self, task):
        if self.request.user.role == User.Role.TECHNICIAN and task.employee.user_id != self.request.user.id:
            raise PermissionDenied("لا يمكنك تعديل مهمة مسندة إلى فني آخر.")

    @action(detail=True, methods=("post",))
    def start(self, request, *args, **kwargs):
        task = self.get_object()
        self._assert_task_actor(task)
        if task.status != JobTask.Status.NOT_STARTED:
            raise ValidationError("لا يمكن بدء مهمة بدأت أو انتهت بالفعل.")
        task.status = JobTask.Status.IN_PROGRESS
        task.started_at = timezone.now()
        task.save(update_fields=("status", "started_at", "updated_at"))
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=("post",))
    def complete(self, request, *args, **kwargs):
        task = self.get_object()
        self._assert_task_actor(task)
        if task.status != JobTask.Status.IN_PROGRESS:
            raise ValidationError("يجب بدء المهمة قبل إكمالها.")
        completed_at = timezone.now()
        task.status = JobTask.Status.COMPLETED
        task.completed_at = completed_at
        task.actual_minutes = max(0, int((completed_at - task.started_at).total_seconds() // 60))
        task.save(update_fields=("status", "completed_at", "actual_minutes", "updated_at"))
        return Response(self.get_serializer(task).data)


class EmployeeCommissionViewSet(WorkshopWorkforceQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = EmployeeCommission.objects.select_related("employee__user", "job_card")
    serializer_class = EmployeeCommissionSerializer
    permission_classes = (IsManagerOrAccountant,)

    def get_queryset(self):
        queryset = super().get_queryset()
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        if year and month:
            queryset = queryset.filter(period__year=year, period__month=month)
        return queryset

    @action(detail=False, methods=("post",))
    def generate(self, request):
        today = date.today()
        try:
            year = int(request.data.get("year", today.year))
            month = int(request.data.get("month", today.month))
            date(year, month, 1)
        except (TypeError, ValueError):
            raise ValidationError("أدخل سنة وشهراً صالحين.")
        records = generate_monthly_commissions(request.user.workshop, year, month)
        return Response(self.get_serializer(records, many=True).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=("get",))
    def summary(self, request):
        queryset = self.get_queryset()
        return Response({"total": queryset.aggregate(total=Sum("amount"))["total"] or 0, "count": queryset.count()})
