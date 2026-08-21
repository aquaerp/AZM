from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction
from django.utils.crypto import salted_hmac
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import AuditEvent, SubscriptionPlan, TrialRegistrationIdentity, User, Workshop, WorkshopSubscription, workshop_has_valid_subscription


class WorkshopSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Workshop
        fields = ("id", "name", "phone", "email", "website", "city", "legal_name", "tax_number", "commercial_registration", "national_address", "street", "district", "building_number", "postal_code", "additional_number", "latitude", "longitude", "auto_deliver_paid_ready_jobs", "logo_url")

    def get_logo_url(self, instance):
        if not instance.logo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(instance.logo.url) if request else instance.logo.url


class WorkshopProfileSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Workshop
        fields = ("id", "name", "phone", "email", "website", "city", "legal_name", "tax_number", "commercial_registration", "national_address", "street", "district", "building_number", "postal_code", "additional_number", "latitude", "longitude", "auto_deliver_paid_ready_jobs", "logo", "logo_url")
        read_only_fields = ("id", "logo_url")

    def get_logo_url(self, instance):
        if not instance.logo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(instance.logo.url) if request else instance.logo.url

    def validate_tax_number(self, value):
        if value and (len(value) != 15 or not value.isdigit()):
            raise serializers.ValidationError("الرقم الضريبي السعودي يجب أن يتكون من 15 رقمًا.")
        return value

    def validate_logo(self, value):
        if value and value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("حجم الشعار يجب ألا يتجاوز 2 ميجابايت.")
        return value


class UserSerializer(serializers.ModelSerializer):
    workshop = WorkshopSerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "email", "role", "workshop", "is_superuser")
        read_only_fields = ("is_superuser",)


class AzmTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if not workshop_has_valid_subscription(self.user.workshop):
            raise serializers.ValidationError("اشتراك الورشة غير نشط أو انتهت مدته. تواصل مع إدارة المنصة.")
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["session_version"] = user.session_version
        return token


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    workshop_name = serializers.CharField(write_only=True, max_length=150)

    class Meta:
        model = User
        fields = ("username", "password", "first_name", "last_name", "email", "workshop_name")

    @staticmethod
    def _identity_hash(kind, value):
        return salted_hmac(f"azm.trial.{kind}", value).hexdigest()

    def validate(self, attrs):
        request = self.context["request"]
        device_id = request.headers.get("X-Azm-Device-Id", "").strip()
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip_address = (forwarded_for.split(",", 1)[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR", "")).strip()
        if len(device_id) < 20 or len(device_id) > 128:
            raise serializers.ValidationError({"detail": "تعذر التحقق من هوية الجهاز. أعد تحميل الصفحة وحاول مجددًا."})
        if not ip_address:
            raise serializers.ValidationError({"detail": "تعذر التحقق من عنوان الاتصال."})
        device_hash = self._identity_hash("device", device_id)
        ip_hash = self._identity_hash("ip", ip_address)
        if TrialRegistrationIdentity.objects.filter(device_hash=device_hash).exists():
            raise serializers.ValidationError({"detail": "سبق استخدام هذا الجهاز لإنشاء فترة تجريبية."})
        if TrialRegistrationIdentity.objects.filter(ip_hash=ip_hash).exists():
            raise serializers.ValidationError({"detail": "سبق استخدام عنوان الاتصال هذا لإنشاء فترة تجريبية."})
        self._trial_device_hash = device_hash
        self._trial_ip_hash = ip_hash
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        workshop_name = validated_data.pop("workshop_name")
        workshop = Workshop.objects.create(name=workshop_name)
        today = timezone.localdate()
        trial_plan, _ = SubscriptionPlan.objects.get_or_create(
            code="trial-14-days",
            defaults={"name": "تجربة 14 يومًا", "monthly_price": 0, "max_users": 3, "is_active": True},
        )
        WorkshopSubscription.objects.create(
            workshop=workshop,
            plan=trial_plan,
            status=WorkshopSubscription.Status.TRIAL,
            started_at=today,
            current_period_end=today + timedelta(days=13),
            auto_renew=False,
        )
        # Public registration creates the workshop's initial owner only.
        user = User.objects.create_user(
            **validated_data,
            workshop=workshop,
            role=User.Role.OWNER,
        )
        try:
            with transaction.atomic():
                TrialRegistrationIdentity.objects.create(
                    workshop=workshop,
                    user=user,
                    device_hash=self._trial_device_hash,
                    ip_hash=self._trial_ip_hash,
                )
        except IntegrityError as error:
            raise serializers.ValidationError({"detail": "سبق استخدام هذا الجهاز أو عنوان الاتصال لإنشاء فترة تجريبية."}) from error
        return user


class StaffMemberCreateSerializer(serializers.ModelSerializer):
    """Minimal account creation used to assign technicians to job cards."""

    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "username", "password", "first_name", "last_name", "email", "role")
        read_only_fields = ("id",)

    def validate_role(self, role):
        if role not in (User.Role.MANAGER, User.Role.TECHNICIAN, User.Role.ACCOUNTANT, User.Role.RECEPTIONIST, User.Role.STOREKEEPER):
            raise serializers.ValidationError("الدور المحدد غير متاح ضمن فريق الورشة.")
        return role

    def validate(self, attrs):
        workshop = self.context["request"].user.workshop
        subscription = getattr(workshop, "subscription", None)
        if subscription and workshop.users.filter(is_active=True).count() >= subscription.plan.max_users:
            raise serializers.ValidationError({"detail": f"بلغت الورشة حد الخطة وهو {subscription.plan.max_users} مستخدمين."})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(workshop=self.context["request"].user.workshop, **validated_data)


class StaffMemberUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "role", "is_active")

    def validate_role(self, role):
        if role == User.Role.OWNER:
            raise serializers.ValidationError("لا يمكن منح ملكية الورشة من واجهة إدارة الفريق.")
        return role

    def update(self, instance, validated_data):
        role_changed = "role" in validated_data and validated_data["role"] != instance.role
        active_changed = "is_active" in validated_data and validated_data["is_active"] != instance.is_active
        instance = super().update(instance, validated_data)
        if role_changed or active_changed:
            type(instance).objects.filter(pk=instance.pk).update(session_version=instance.session_version + 1)
            instance.refresh_from_db(fields=("session_version",))
        return instance


class AuditEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AuditEvent
        fields = ("id", "actor", "actor_username", "action", "entity_type", "entity_id", "before", "after", "ip_address", "created_at")
        read_only_fields = fields


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    subscriptions_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = SubscriptionPlan
        fields = ("id", "name", "code", "monthly_price", "max_users", "is_active", "subscriptions_count", "created_at", "updated_at")
        read_only_fields = ("id", "subscriptions_count", "created_at", "updated_at")


class WorkshopSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = WorkshopSubscription
        fields = ("id", "plan", "plan_name", "status", "started_at", "current_period_end", "auto_renew", "notes", "updated_at")
        read_only_fields = ("id", "plan_name", "updated_at")


class PlatformWorkshopSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(read_only=True)
    owner_username = serializers.CharField(read_only=True)
    subscription = WorkshopSubscriptionSerializer(read_only=True)

    class Meta:
        model = Workshop
        fields = ("id", "name", "phone", "city", "legal_name", "created_at", "users_count", "owner_username", "subscription")
