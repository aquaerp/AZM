from rest_framework import serializers

from accounts.models import User

from .models import Employee, EmployeeCommission, JobTask


class EmployeeSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Employee
        fields = ("id", "user", "username", "user_name", "job_title", "hired_at", "commission_rate", "is_active", "notes", "created_at")
        read_only_fields = ("id", "username", "user_name", "created_at")

    def get_user_name(self, instance):
        return instance.user.get_full_name() or instance.user.username

    def validate_user(self, user):
        request = self.context["request"]
        if user.workshop_id != request.user.workshop_id or user.role != User.Role.TECHNICIAN:
            raise serializers.ValidationError("يجب اختيار حساب فني من الورشة نفسها.")
        return user


class JobTaskSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.user.get_full_name", read_only=True)
    job_number = serializers.CharField(source="job_card.job_number", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = JobTask
        fields = ("id", "job_card", "job_number", "employee", "employee_name", "title", "description", "status", "status_label", "estimated_hours", "actual_minutes", "started_at", "completed_at", "created_at")
        read_only_fields = ("id", "status", "status_label", "actual_minutes", "started_at", "completed_at", "created_at")

    def validate(self, attributes):
        workshop_id = self.context["request"].user.workshop_id
        job_card = attributes.get("job_card", getattr(self.instance, "job_card", None))
        employee = attributes.get("employee", getattr(self.instance, "employee", None))
        if not workshop_id or job_card.workshop_id != workshop_id or employee.workshop_id != workshop_id:
            raise serializers.ValidationError("يجب أن تنتمي المهمة والموظف وبطاقة العمل إلى الورشة نفسها.")
        if not employee.is_active:
            raise serializers.ValidationError({"employee": "لا يمكن تعيين مهمة لموظف غير نشط."})
        return attributes


class EmployeeCommissionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.user.get_full_name", read_only=True)
    job_number = serializers.CharField(source="job_card.job_number", read_only=True)

    class Meta:
        model = EmployeeCommission
        fields = ("id", "employee", "employee_name", "job_card", "job_number", "period", "commission_rate", "basis_amount", "amount", "generated_at")
        read_only_fields = fields
