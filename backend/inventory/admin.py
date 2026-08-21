from django.contrib import admin

from .models import InventoryAlert, Part, PartUsage, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "workshop", "is_active")
    list_filter = ("workshop", "is_active")
    search_fields = ("name", "phone")


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "quantity", "reorder_level", "supplier", "workshop")
    list_filter = ("workshop", "is_active")
    search_fields = ("sku", "name")


@admin.register(PartUsage)
class PartUsageAdmin(admin.ModelAdmin):
    list_display = ("part", "quantity", "job_card", "workshop", "created_at")
    list_filter = ("workshop",)
    search_fields = ("part__sku", "job_card__job_number")


@admin.register(InventoryAlert)
class InventoryAlertAdmin(admin.ModelAdmin):
    list_display = ("part", "quantity_at_alert", "reorder_level_at_alert", "is_active", "workshop", "created_at")
    list_filter = ("workshop", "is_active")
