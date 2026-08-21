from django.contrib import admin

from .models import Customer, JobCard, Service, Vehicle


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "workshop", "created_at")
    search_fields = ("name", "phone")
    list_filter = ("workshop",)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("license_plate", "make", "model", "customer", "workshop")
    search_fields = ("license_plate", "vin", "customer__name")
    list_filter = ("workshop", "make")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "base_price", "workshop", "is_active")
    list_filter = ("workshop", "is_active")


@admin.register(JobCard)
class JobCardAdmin(admin.ModelAdmin):
    list_display = ("job_number", "vehicle", "status", "workshop", "received_at")
    search_fields = ("job_number", "vehicle__license_plate", "customer__name")
    list_filter = ("workshop", "status")
    filter_horizontal = ("services", "assigned_technicians")
