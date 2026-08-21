from decimal import Decimal
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from accounts.models import Workshop


class WorkshopOwnedModel(models.Model):
    """Shared tenant key for all operational data."""

    workshop = models.ForeignKey(Workshop, on_delete=models.PROTECT, related_name="%(class)ss")

    class Meta:
        abstract = True


class Customer(WorkshopOwnedModel):
    name = models.CharField("اسم العميل", max_length=150)
    phone = models.CharField("رقم الهاتف", max_length=30)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    notes = models.TextField("ملاحظات", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        indexes = [models.Index(fields=("workshop", "name")), models.Index(fields=("workshop", "phone"))]
        verbose_name = "عميل"
        verbose_name_plural = "العملاء"

    def __str__(self):
        return self.name


class Vehicle(WorkshopOwnedModel):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="vehicles")
    license_plate = models.CharField("رقم اللوحة", max_length=30)
    make = models.CharField("الشركة المصنعة", max_length=80)
    model = models.CharField("الموديل", max_length=80)
    model_year = models.PositiveSmallIntegerField("سنة الصنع", null=True, blank=True)
    vin = models.CharField("رقم الهيكل", max_length=50, blank=True)
    color = models.CharField("اللون", max_length=50, blank=True)
    mileage = models.PositiveIntegerField("عداد الكيلومترات", null=True, blank=True)
    notes = models.TextField("ملاحظات", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("license_plate",)
        constraints = [models.UniqueConstraint(fields=("workshop", "license_plate"), name="unique_plate_per_workshop")]
        indexes = [models.Index(fields=("workshop", "vin"))]
        verbose_name = "مركبة"
        verbose_name_plural = "المركبات"

    def clean(self):
        if self.customer_id and self.workshop_id and self.customer.workshop_id != self.workshop_id:
            raise ValidationError({"customer": "يجب أن ينتمي العميل والمركبة إلى الورشة نفسها."})

    def __str__(self):
        return f"{self.make} {self.model} — {self.license_plate}"


class Service(WorkshopOwnedModel):
    name = models.CharField("اسم الخدمة", max_length=150)
    description = models.TextField("الوصف", blank=True)
    base_price = models.DecimalField("السعر الأساسي", max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    is_active = models.BooleanField("نشطة", default=True)

    class Meta:
        ordering = ("name",)
        constraints = [models.UniqueConstraint(fields=("workshop", "name"), name="unique_service_per_workshop")]
        verbose_name = "خدمة"
        verbose_name_plural = "الخدمات"

    def __str__(self):
        return self.name


class JobCard(WorkshopOwnedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "بانتظار الفحص"
        IN_PROGRESS = "in_progress", "قيد الإصلاح"
        READY = "ready", "جاهزة للاستلام"
        DELIVERED = "delivered", "تم التسليم"
        CANCELLED = "cancelled", "ملغاة"

    job_number = models.CharField("رقم بطاقة العمل", max_length=20, unique=True, editable=False, blank=True)
    portal_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="job_cards")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="job_cards")
    services = models.ManyToManyField(Service, related_name="job_cards", blank=True)
    assigned_technicians = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="assigned_job_cards", blank=True)
    status = models.CharField("الحالة", max_length=20, choices=Status.choices, default=Status.PENDING)
    complaint = models.TextField("وصف العطل")
    diagnosis = models.TextField("نتيجة الفحص", blank=True)
    estimated_cost = models.DecimalField("التكلفة التقديرية", max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    actual_cost = models.DecimalField("التكلفة الفعلية", max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    received_at = models.DateTimeField("تاريخ الاستلام", auto_now_add=True)
    promised_at = models.DateTimeField("موعد الإنجاز المتوقع", null=True, blank=True)
    status_updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField("تاريخ التسليم الفعلي", null=True, blank=True)
    delivered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="delivered_job_cards", null=True, blank=True)
    delivery_method = models.CharField("طريقة التسليم", max_length=20, choices=(("manual", "يدوي"), ("automatic", "آلي")), blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_job_cards")

    class Meta:
        ordering = ("-received_at",)
        indexes = [models.Index(fields=("workshop", "status")), models.Index(fields=("workshop", "received_at"))]
        verbose_name = "بطاقة عمل"
        verbose_name_plural = "بطاقات العمل"

    def clean(self):
        errors = {}
        if self.customer_id and self.workshop_id and self.customer.workshop_id != self.workshop_id:
            errors["customer"] = "العميل لا ينتمي إلى هذه الورشة."
        if self.vehicle_id and self.workshop_id and self.vehicle.workshop_id != self.workshop_id:
            errors["vehicle"] = "المركبة لا تنتمي إلى هذه الورشة."
        if self.customer_id and self.vehicle_id and self.vehicle.customer_id != self.customer_id:
            errors["vehicle"] = "يجب أن تكون المركبة مرتبطة بالعميل المحدد."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.job_number:
            self.job_number = f"JC-{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(job_number=self.job_number)

    @property
    def services_total(self):
        return sum((service.base_price for service in self.services.all()), Decimal("0.00"))

    def __str__(self):
        return self.job_number or "بطاقة عمل جديدة"
