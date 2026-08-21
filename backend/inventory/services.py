from .models import InventoryAlert, Part


def sync_low_stock_alert(part: Part) -> InventoryAlert | None:
    """Keep the active in-app alert aligned with a part's stock level."""

    active_alert = InventoryAlert.objects.filter(part=part, is_active=True).first()
    if part.quantity <= part.reorder_level:
        if active_alert:
            active_alert.quantity_at_alert = part.quantity
            active_alert.reorder_level_at_alert = part.reorder_level
            active_alert.save(update_fields=("quantity_at_alert", "reorder_level_at_alert", "updated_at"))
            return active_alert
        return InventoryAlert.objects.create(
            workshop=part.workshop,
            part=part,
            quantity_at_alert=part.quantity,
            reorder_level_at_alert=part.reorder_level,
        )
    if active_alert:
        active_alert.is_active = False
        active_alert.save(update_fields=("is_active", "updated_at"))
    return None
