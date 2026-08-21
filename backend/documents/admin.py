from django.contrib import admin

from .models import Document, DocumentExpiryAlert


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "document_type", "expires_at", "workshop", "created_at")
    list_filter = ("workshop", "document_type")
    search_fields = ("name", "original_filename")


@admin.register(DocumentExpiryAlert)
class DocumentExpiryAlertAdmin(admin.ModelAdmin):
    list_display = ("document", "days_before", "acknowledged_at", "workshop", "created_at")
    list_filter = ("workshop", "days_before")
