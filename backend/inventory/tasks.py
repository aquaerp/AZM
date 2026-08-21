from celery import shared_task

from .models import Part
from .services import sync_low_stock_alert


@shared_task
def check_low_stock_levels():
    """Daily Celery Beat task to create or resolve in-app low-stock alerts."""

    count = 0
    for part in Part.objects.filter(is_active=True).select_related("workshop"):
        if sync_low_stock_alert(part):
            count += 1
    return count
