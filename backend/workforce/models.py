from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from workshop.models import JobCard, WorkshopOwnedModel


class Employee(WorkshopOwnedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="employee_profile")
    job_title = models.CharField("المسمى الوظيفي", max_length=100, default="فني")
    hired_at = models.DateField("تاريخ التوظيف")
    commission_rate = models.DecimalField("نسبة العمولة", max_digits=5, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))])
    is_active = models.BooleanField("نشط", default=True)
    notes = models.TextField("ملاحظات", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("user__first_name", "user__username")
        verbose_name = "موظف"
        verbose_name_plural = "الموظفون"

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class JobTask(WorkshopOwnedModel):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "لم تبدأ"
        IN_PROGRESS = "in_progress", "قيد التنفيذ"
        COMPLETED = "completed", "مكتملة"
        CANCELLED = "cancelled", "ملغاة"

    job_card = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name="tasks")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="tasks")
    title = models.CharField("اسم المهمة", max_length=180)
    description = models.TextField("الوصف", blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    estimated_hours = models.DecimalField("الساعات التقديرية", max_digits=6, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    actual_minutes = models.PositiveIntegerField("الدقائق الفعلية", default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("workshop", "employee", "status")), models.Index(fields=("workshop", "job_card"))]
        verbose_name = "مهمة"
        verbose_name_plural = "المهام"

    def __str__(self):
        return self.title


class EmployeeCommission(WorkshopOwnedModel):
    """An immutable monthly snapshot per employee and delivered job card."""

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="commissions")
    job_card = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name="commissions")
    period = models.DateField("فترة الاستحقاق")
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    basis_amount = models.DecimalField("قيمة العمل بعد التوزيع", max_digits=12, decimal_places=2)
    amount = models.DecimalField("قيمة العمولة", max_digits=12, decimal_places=2)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-period", "employee__user__first_name")
        constraints = [models.UniqueConstraint(fields=("employee", "job_card"), name="one_commission_per_employee_job")]
        indexes = [models.Index(fields=("workshop", "period"))]
        verbose_name = "عمولة موظف"
        verbose_name_plural = "عمولات الموظفين"

    def __str__(self):
        return f"{self.employee} — {self.job_card}"
