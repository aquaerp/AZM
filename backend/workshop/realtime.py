"""Small, tenant-scoped real-time event helpers."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def workshop_group_name(workshop_id):
    return f"workshop_{workshop_id}"


def publish_workshop_update(workshop_id, entity, record_id, job_card_id=None):
    """Broadcast an opaque refresh hint only; operational data stays behind the API."""

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        workshop_group_name(workshop_id),
        {
            "type": "workshop.update",
            "entity": entity,
            "record_id": record_id,
            "job_card_id": job_card_id,
        },
    )
