from pathlib import Path

from django.core.files.base import ContentFile
from rest_framework import serializers

from .crypto import encrypt
from .models import Document, DocumentExpiryAlert


class DocumentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    owner_label = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ("id", "name", "document_type", "customer", "vehicle", "employee", "owner_label", "original_filename", "content_type", "file", "expires_at", "download_url", "created_at", "updated_at")
        read_only_fields = ("id", "owner_label", "original_filename", "content_type", "download_url", "created_at", "updated_at")

    def get_owner_label(self, instance):
        if instance.customer:
            return instance.customer.name
        if instance.vehicle:
            return str(instance.vehicle)
        if instance.employee:
            return str(instance.employee)
        return "الورشة"

    def get_download_url(self, instance):
        request = self.context.get("request")
        path = f"/api/documents/documents/{instance.id}/download/"
        return request.build_absolute_uri(path) if request else path

    def validate(self, attributes):
        request = self.context["request"]
        owners = [attributes.get("customer", getattr(self.instance, "customer", None)), attributes.get("vehicle", getattr(self.instance, "vehicle", None)), attributes.get("employee", getattr(self.instance, "employee", None))]
        if sum(owner is not None for owner in owners) > 1:
            raise serializers.ValidationError("اربط الوثيقة بعميل أو مركبة أو موظف واحد فقط.")
        for owner in owners:
            if owner is not None and owner.workshop_id != request.user.workshop_id:
                raise serializers.ValidationError("الجهة المرتبطة بالوثيقة لا تنتمي إلى ورشتك.")
        upload = attributes.get("file")
        if upload and upload.size > self.context["request"].parser_context["view"].document_max_upload_bytes:
            raise serializers.ValidationError({"file": "حجم الملف يتجاوز الحد المسموح."})
        if not self.instance and not upload:
            raise serializers.ValidationError({"file": "الملف مطلوب عند رفع وثيقة جديدة."})
        return attributes

    def create(self, validated_data):
        upload = validated_data.pop("file")
        payload = upload.read()
        encrypted = encrypt(payload)
        document = Document(
            workshop=self.context["request"].user.workshop,
            uploaded_by=self.context["request"].user,
            original_filename=Path(upload.name).name,
            content_type=upload.content_type or "application/octet-stream",
            **validated_data,
        )
        document.encrypted_file.save(f"{Path(upload.name).name}.enc", ContentFile(encrypted), save=False)
        document.save()
        return document


class DocumentExpiryAlertSerializer(serializers.ModelSerializer):
    document_name = serializers.CharField(source="document.name", read_only=True)
    expires_at = serializers.DateField(source="document.expires_at", read_only=True)

    class Meta:
        model = DocumentExpiryAlert
        fields = ("id", "document", "document_name", "expires_at", "days_before", "acknowledged_at", "created_at")
        read_only_fields = fields
