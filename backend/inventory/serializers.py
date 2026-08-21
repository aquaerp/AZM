from django.db import transaction
from rest_framework import serializers

from workshop.models import JobCard

from .models import InventoryAlert, Part, PartRequest, PartUsage, Supplier
from .services import sync_low_stock_alert


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ("id", "name", "contact_name", "phone", "email", "notes", "is_active")
        read_only_fields = ("id",)


class PartSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Part
        fields = ("id", "name", "sku", "description", "supplier", "supplier_name", "quantity", "reorder_level", "purchase_price", "sale_price", "is_active", "is_low_stock", "created_at", "updated_at")
        read_only_fields = ("id", "supplier_name", "is_low_stock", "created_at", "updated_at")

    def validate_supplier(self, supplier):
        if supplier and supplier.workshop_id != self.context["request"].user.workshop_id:
            raise serializers.ValidationError("المورد لا ينتمي إلى ورشتك.")
        return supplier


class PartUsageSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source="part.name", read_only=True)
    part_sku = serializers.CharField(source="part.sku", read_only=True)
    job_number = serializers.CharField(source="job_card.job_number", read_only=True)
    total_sale_value = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = PartUsage
        fields = ("id", "job_card", "job_number", "part", "part_name", "part_sku", "quantity", "unit_purchase_price", "unit_sale_price", "total_sale_value", "created_at")
        read_only_fields = ("id", "part_name", "part_sku", "job_number", "unit_purchase_price", "unit_sale_price", "total_sale_value", "created_at")

    def validate(self, attributes):
        workshop_id = self.context["request"].user.workshop_id
        part = attributes["part"]
        job_card = attributes["job_card"]
        if not workshop_id or part.workshop_id != workshop_id or job_card.workshop_id != workshop_id:
            raise serializers.ValidationError("يجب أن تنتمي القطعة وبطاقة العمل إلى ورشتك.")
        return attributes

    @transaction.atomic
    def create(self, validated_data):
        part = Part.objects.select_for_update().select_related("workshop").get(pk=validated_data.pop("part").pk)
        quantity = validated_data["quantity"]
        if part.quantity < quantity:
            raise serializers.ValidationError({"quantity": f"الكمية المتاحة للقطعة هي {part.quantity} فقط."})
        part.quantity -= quantity
        part.save(update_fields=("quantity", "updated_at"))
        usage = PartUsage.objects.create(
            **validated_data,
            part=part,
            workshop=part.workshop,
            added_by=self.context["request"].user,
            unit_purchase_price=part.purchase_price,
            unit_sale_price=part.sale_price,
        )
        sync_low_stock_alert(part)
        return usage


class InventoryAlertSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source="part.name", read_only=True)
    part_sku = serializers.CharField(source="part.sku", read_only=True)

    class Meta:
        model = InventoryAlert
        fields = ("id", "part", "part_name", "part_sku", "quantity_at_alert", "reorder_level_at_alert", "is_active", "acknowledged_at", "created_at")
        read_only_fields = fields


class PartRequestSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source="part.name", read_only=True)
    part_sku = serializers.CharField(source="part.sku", read_only=True)
    job_number = serializers.CharField(source="job_card.job_number", read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PartRequest
        fields = ("id", "job_card", "job_number", "part", "part_name", "part_sku", "quantity", "notes", "status", "status_label", "requested_by", "requested_by_name", "reviewed_by", "fulfilled_usage", "created_at", "reviewed_at")
        read_only_fields = ("id", "job_number", "part_name", "part_sku", "status", "status_label", "requested_by", "requested_by_name", "reviewed_by", "fulfilled_usage", "created_at", "reviewed_at")

    def get_requested_by_name(self, instance):
        return instance.requested_by.get_full_name() or instance.requested_by.username

    def validate(self, attributes):
        request = self.context["request"]
        job_card = attributes["job_card"]
        part = attributes["part"]
        if job_card.workshop_id != request.user.workshop_id or part.workshop_id != request.user.workshop_id:
            raise serializers.ValidationError("يجب أن تنتمي البطاقة والقطعة إلى ورشتك.")
        if request.user.role == "technician" and not job_card.assigned_technicians.filter(pk=request.user.pk).exists():
            raise serializers.ValidationError({"job_card": "لا يمكنك طلب قطع لبطاقة غير مسندة إليك."})
        if job_card.status not in (JobCard.Status.PENDING, JobCard.Status.IN_PROGRESS):
            raise serializers.ValidationError({"job_card": "يمكن طلب القطع للبطاقات قيد العمل فقط."})
        return attributes
