from django.conf import settings
from django.db import models

from workforce.models import Employee
from workshop.models import Customer, Vehicle, WorkshopOwnedModel


class Document(WorkshopOwnedModel):
    name = models.CharField("اسم الوثيقة", max_length=180)
    document_type = models.CharField("نوع الوثيقة", max_length=100)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="documents", null=True, blank=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="documents", null=True, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="documents", null=True, blank=True)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120, blank=True)
    encrypted_file = models.FileField(upload_to="documents/%Y/%m/")
    expires_at = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_documents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("expires_at", "-created_at")
        indexes = [models.Index(fields=("workshop", "expires_at")), models.Index(fields=("workshop", "document_type"))]
        verbose_name = "وثيقة"
        verbose_name_plural = "الوثائق"

    def __str__(self):
        return self.name


class DocumentExpiryAlert(WorkshopOwnedModel):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="expiry_alerts")
    days_before = models.PositiveSmallIntegerField()
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [models.UniqueConstraint(fields=("document", "days_before"), name="one_expiry_alert_per_threshold")]
        verbose_name = "تنبيه انتهاء وثيقة"
        verbose_name_plural = "تنبيهات انتهاء الوثائق"

    def __str__(self):
        return f"{self.document} - {self.days_before} يوم"
