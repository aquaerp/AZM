from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import SubscriptionPlan, TrialRegistrationIdentity, User, Workshop, WorkshopSubscription


@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "phone", "created_at")
    search_fields = ("name", "city", "phone")


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "monthly_price", "max_users", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(WorkshopSubscription)
class WorkshopSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("workshop", "plan", "status", "current_period_end", "auto_renew", "updated_at")
    list_filter = ("status", "plan", "auto_renew")
    search_fields = ("workshop__name", "workshop__phone")
    autocomplete_fields = ("workshop", "plan")


@admin.register(TrialRegistrationIdentity)
class TrialRegistrationIdentityAdmin(admin.ModelAdmin):
    list_display = ("workshop", "user", "created_at")
    search_fields = ("workshop__name", "user__username", "user__email")
    readonly_fields = ("workshop", "user", "device_hash", "ip_hash", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(User)
class AzmUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "workshop", "role", "is_staff")
    list_filter = ("role", "workshop", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (("بيانات عزم", {"fields": ("workshop", "role")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("بيانات عزم", {"fields": ("workshop", "role")}),)

# Register your models here.
