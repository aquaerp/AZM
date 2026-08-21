from datetime import date

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import Document, DocumentExpiryAlert


ALERT_DAYS = (45, 30, 7)


@shared_task
def check_document_expirations():
    """Creates an in-app alert once for each 45/30/7-day document threshold."""

    today = date.today()
    created = 0
    documents = Document.objects.filter(expires_at__isnull=False).select_related("workshop")
    for document in documents:
        days_remaining = (document.expires_at - today).days
        if days_remaining not in ALERT_DAYS:
            continue
        alert, was_created = DocumentExpiryAlert.objects.get_or_create(
            workshop=document.workshop,
            document=document,
            days_before=days_remaining,
        )
        if was_created:
            created += 1
            if settings.DOCUMENT_ALERT_EMAILS:
                send_mail(
                    subject=f"تنبيه عزم: تنتهي وثيقة {document.name} خلال {days_remaining} يوماً",
                    message=f"تنتهي الوثيقة {document.name} في {document.expires_at}.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=settings.DOCUMENT_ALERT_EMAILS,
                    fail_silently=True,
                )
    return created
