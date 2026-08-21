from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Workshop(models.Model):
    """A workshop tenant. Business modules will always be scoped to it."""

    name = models.CharField("اسم الورشة", max_length=150)
    phone = models.CharField("رقم الهاتف", max_length=30, blank=True)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    website = models.URLField("الموقع الإلكتروني", blank=True)
    city = models.CharField("المدينة", max_length=100, blank=True)
    legal_name = models.CharField("الاسم القانوني", max_length=200, blank=True)
    tax_number = models.CharField("الرقم الضريبي", max_length=15, blank=True)
    commercial_registration = models.CharField("رقم السجل التجاري", max_length=30, blank=True)
    national_address = models.TextField("العنوان الوطني", blank=True)
    street = models.CharField("الشارع", max_length=150, blank=True)
    district = models.CharField("الحي", max_length=100, blank=True)
    building_number = models.CharField("رقم المبنى", max_length=20, blank=True)
    postal_code = models.CharField("الرمز البريدي", max_length=10, blank=True)
    additional_number = models.CharField("الرقم الإضافي", max_length=10, blank=True)
    latitude = models.DecimalField("خط العرض", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("خط الطول", max_digits=9, decimal_places=6, null=True, blank=True)
    logo = models.ImageField("شعار الورشة", upload_to="workshop-logos/", blank=True)
    auto_deliver_paid_ready_jobs = models.BooleanField("تسليم البطاقة الجاهزة آليًا بعد اكتمال السداد", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ورشة"
        verbose_name_plural = "الورش"

    def __str__(self):
        return self.name


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=50, unique=True)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_users = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("monthly_price", "name")

    def __str__(self):
        return self.name


class WorkshopSubscription(models.Model):
    class Status(models.TextChoices):
        TRIAL = "trial", "فترة تجريبية"
        ACTIVE = "active", "نشط"
        PAST_DUE = "past_due", "متأخر"
        SUSPENDED = "suspended", "معلق"
        CANCELLED = "cancelled", "ملغي"

    workshop = models.OneToOneField(Workshop, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIAL)
    started_at = models.DateField()
    current_period_end = models.DateField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("current_period_end", "workshop__name")

    def __str__(self):
        return f"{self.workshop} — {self.plan}"

    @property
    def allows_access(self):
        if self.status not in (self.Status.TRIAL, self.Status.ACTIVE):
            return False
        return not self.current_period_end or self.current_period_end >= timezone.localdate()


def workshop_has_valid_subscription(workshop):
    if workshop is None:
        return True
    try:
        return workshop.subscription.allows_access
    except WorkshopSubscription.DoesNotExist:
        return False


class TrialRegistrationIdentity(models.Model):
    workshop = models.OneToOneField(Workshop, on_delete=models.CASCADE, related_name="trial_identity")
    user = models.OneToOneField("User", on_delete=models.CASCADE, related_name="trial_identity")
    device_hash = models.CharField(max_length=64, unique=True)
    ip_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"trial-registration:{self.workshop_id}"


class User(AbstractUser):
    class Role(models.TextChoices):
        OWNER = "owner", "مالك الورشة"
        MANAGER = "manager", "مدير الورشة"
        TECHNICIAN = "technician", "فني"
        ACCOUNTANT = "accountant", "محاسب"
        RECEPTIONIST = "receptionist", "موظف استقبال"
        STOREKEEPER = "storekeeper", "أمين مخزن"

    workshop = models.ForeignKey(
        Workshop,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TECHNICIAN)
    session_version = models.PositiveIntegerField(default=0, editable=False)

    @property
    def is_workshop_manager(self):
        return self.role in (self.Role.OWNER, self.Role.MANAGER)


class AuditEvent(models.Model):
    workshop = models.ForeignKey(Workshop, on_delete=models.PROTECT, related_name="audit_events")
    actor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="audit_events")
    action = models.CharField(max_length=80)
    entity_type = models.CharField(max_length=120)
    entity_id = models.CharField(max_length=80, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [models.Index(fields=("workshop", "created_at")), models.Index(fields=("workshop", "entity_type", "entity_id"))]

    def __str__(self):
        return f"{self.action}: {self.entity_type}#{self.entity_id}"

# Create your models here.
