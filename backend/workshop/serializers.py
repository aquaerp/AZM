from django.db import transaction
from rest_framework import serializers

from accounts.models import User
from accounts.serializers import UserSerializer

from .models import Customer, JobCard, Service, Vehicle


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "name", "phone", "email", "notes", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class VehicleSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = Vehicle
        fields = ("id", "customer", "customer_name", "license_plate", "make", "model", "model_year", "vin", "color", "mileage", "notes", "created_at", "updated_at")
        read_only_fields = ("id", "customer_name", "created_at", "updated_at")

    def validate_customer(self, customer):
        request = self.context["request"]
        if customer.workshop_id != request.user.workshop_id:
            raise serializers.ValidationError("العميل لا ينتمي إلى ورشتك.")
        return customer


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ("id", "name", "description", "base_price", "is_active")
        read_only_fields = ("id",)


class JobCardListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    vehicle_label = serializers.SerializerMethodField()
    assigned_technicians = UserSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = JobCard
        fields = ("id", "job_number", "customer_name", "vehicle_label", "status", "status_label", "complaint", "estimated_cost", "received_at", "promised_at", "status_updated_at", "delivered_at", "delivery_method", "assigned_technicians")

    def get_vehicle_label(self, instance):
        return str(instance.vehicle)


class JobCardDetailSerializer(JobCardListSerializer):
    customer = CustomerSerializer(read_only=True)
    vehicle = VehicleSerializer(read_only=True)
    services = ServiceSerializer(many=True, read_only=True)
    diagnosis = serializers.CharField(read_only=True)
    actual_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    services_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta(JobCardListSerializer.Meta):
        fields = JobCardListSerializer.Meta.fields + ("customer", "vehicle", "services", "diagnosis", "actual_cost", "services_total", "portal_token")


class PublicJobStatusSerializer(serializers.ModelSerializer):
    vehicle = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    invoice = serializers.SerializerMethodField()

    class Meta:
        model = JobCard
        fields = ("job_number", "vehicle", "status", "status_label", "received_at", "promised_at", "delivered_at", "invoice")

    def get_vehicle(self, instance):
        return f"{instance.vehicle.make} {instance.vehicle.model} — {instance.vehicle.license_plate}"

    def get_invoice(self, instance):
        try:
            invoice = instance.invoice
        except Exception:
            return None
        return {"status": invoice.status, "status_label": invoice.get_status_display(), "total": str(invoice.total), "amount_paid": str(invoice.amount_paid)}


class JobCardWriteSerializer(serializers.ModelSerializer):
    service_ids = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), many=True, source="services", required=False, write_only=True)
    technician_ids = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, source="assigned_technicians", required=False, write_only=True)

    class Meta:
        model = JobCard
        fields = ("id", "customer", "vehicle", "service_ids", "technician_ids", "status", "complaint", "diagnosis", "estimated_cost", "actual_cost", "promised_at")
        read_only_fields = ("id",)

    def validate(self, attributes):
        request = self.context["request"]
        workshop_id = request.user.workshop_id
        customer = attributes.get("customer", getattr(self.instance, "customer", None))
        vehicle = attributes.get("vehicle", getattr(self.instance, "vehicle", None))
        services = attributes.get("services", None)
        technicians = attributes.get("assigned_technicians", None)

        if not workshop_id:
            raise serializers.ValidationError("لا يرتبط حسابك بورشة.")
        if customer and customer.workshop_id != workshop_id:
            raise serializers.ValidationError({"customer": "العميل لا ينتمي إلى ورشتك."})
        if vehicle and vehicle.workshop_id != workshop_id:
            raise serializers.ValidationError({"vehicle": "المركبة لا تنتمي إلى ورشتك."})
        if customer and vehicle and vehicle.customer_id != customer.id:
            raise serializers.ValidationError({"vehicle": "المركبة لا تتبع العميل المحدد."})
        if services is not None and any(service.workshop_id != workshop_id for service in services):
            raise serializers.ValidationError({"service_ids": "تتضمن الخدمات خدمة من ورشة أخرى."})
        if technicians is not None:
            for technician in technicians:
                if technician.workshop_id != workshop_id or technician.role != User.Role.TECHNICIAN:
                    raise serializers.ValidationError({"technician_ids": "يمكن تعيين فنيين من الورشة نفسها فقط."})
        return attributes

    @transaction.atomic
    def create(self, validated_data):
        services = validated_data.pop("services", [])
        technicians = validated_data.pop("assigned_technicians", [])
        request = self.context["request"]
        job_card = JobCard.objects.create(workshop=request.user.workshop, created_by=request.user, **validated_data)
        if services:
            job_card.services.set(services)
        if technicians:
            job_card.assigned_technicians.set(technicians)
        return job_card

    @transaction.atomic
    def update(self, instance, validated_data):
        services = validated_data.pop("services", None)
        technicians = validated_data.pop("assigned_technicians", None)
        instance = super().update(instance, validated_data)
        if services is not None:
            instance.services.set(services)
        if technicians is not None:
            instance.assigned_technicians.set(technicians)
        return instance


class JobStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobCard
        fields = ("status", "diagnosis", "actual_cost")


class JobScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobCard
        fields = ("promised_at",)
