from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from workshop.models import JobCard, WorkshopOwnedModel


class Supplier(WorkshopOwnedModel):
    name = models.CharField("اسم المورد", max_length=150)
    contact_name = models.CharField("جهة الاتصال", max_length=150, blank=True)
    phone = models.CharField("الهاتف", max_length=30, blank=True)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    notes = models.TextField("ملاحظات", blank=True)
    is_active = models.BooleanField("نشط", default=True)

    class Meta:
        ordering = ("name",)
        constraints = [models.UniqueConstraint(fields=("workshop", "name"), name="unique_supplier_per_workshop")]
        verbose_name = "مورد"
        verbose_name_plural = "الموردون"

    def __str__(self):
        return self.name


class Part(WorkshopOwnedModel):
    name = models.CharField("اسم القطعة", max_length=150)
    sku = models.CharField("رمز القطعة", max_length=80)
    description = models.TextField("الوصف", blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, related_name="parts", null=True, blank=True)
    quantity = models.PositiveIntegerField("الكمية المتاحة", default=0)
    reorder_level = models.PositiveIntegerField("حد إعادة الطلب", default=0)
    purchase_price = models.DecimalField("سعر الشراء", max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    sale_price = models.DecimalField("سعر البيع", max_digits=12, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    is_active = models.BooleanField("نشطة", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [models.UniqueConstraint(fields=("workshop", "sku"), name="unique_sku_per_workshop")]
        indexes = [models.Index(fields=("workshop", "quantity", "reorder_level"))]
        verbose_name = "قطعة غيار"
        verbose_name_plural = "قطع الغيار"

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    def __str__(self):
        return f"{self.sku} — {self.name}"


class PartUsage(WorkshopOwnedModel):
    """A stock movement for a part consumed by a job card."""

    job_card = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name="part_usages")
    part = models.ForeignKey(Part, on_delete=models.PROTECT, related_name="usages")
    quantity = models.PositiveIntegerField("الكمية المصروفة", validators=[MinValueValidator(1)])
    unit_purchase_price = models.DecimalField("سعر الشراء وقت الصرف", max_digits=12, decimal_places=2)
    unit_sale_price = models.DecimalField("سعر البيع وقت الصرف", max_digits=12, decimal_places=2)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="part_usages_added")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("workshop", "job_card"))]
        verbose_name = "صرف قطعة"
        verbose_name_plural = "حركات صرف القطع"

    @property
    def total_sale_value(self):
        return self.quantity * self.unit_sale_price


class InventoryAlert(WorkshopOwnedModel):
    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name="alerts")
    quantity_at_alert = models.PositiveIntegerField()
    reorder_level_at_alert = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [models.UniqueConstraint(fields=("part",), condition=Q(is_active=True), name="one_active_alert_per_part")]
        verbose_name = "تنبيه مخزون"
        verbose_name_plural = "تنبيهات المخزون"

    def __str__(self):
        return f"تنبيه مخزون: {self.part}"


class PartRequest(WorkshopOwnedModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "مطلوبة"
        APPROVED = "approved", "معتمدة"
        FULFILLED = "fulfilled", "تم الصرف"
        REJECTED = "rejected", "مرفوضة"

    job_card = models.ForeignKey(JobCard, on_delete=models.PROTECT, related_name="part_requests")
    part = models.ForeignKey(Part, on_delete=models.PROTECT, related_name="requests")
    quantity = models.PositiveIntegerField("الكمية المطلوبة", validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    notes = models.TextField("ملاحظات الفني", blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="part_requests_created")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="part_requests_reviewed", null=True, blank=True)
    fulfilled_usage = models.OneToOneField(PartUsage, on_delete=models.PROTECT, related_name="source_request", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("workshop", "status"), name="inventory_p_worksho_req_idx"),
            models.Index(fields=("workshop", "requested_by"), name="inventory_p_worksho_user_idx"),
        ]
