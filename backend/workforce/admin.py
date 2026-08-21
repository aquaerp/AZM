from django.contrib import admin

from .models import Employee, EmployeeCommission, JobTask


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("user", "job_title", "commission_rate", "workshop", "is_active")
    list_filter = ("workshop", "is_active")
    search_fields = ("user__username", "user__first_name", "user__last_name")


@admin.register(JobTask)
class JobTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "employee", "job_card", "status", "actual_minutes")
    list_filter = ("workshop", "status")
    search_fields = ("title", "job_card__job_number")


@admin.register(EmployeeCommission)
class EmployeeCommissionAdmin(admin.ModelAdmin):
    list_display = ("employee", "job_card", "period", "commission_rate", "amount")
    list_filter = ("workshop", "period")
