from urllib.parse import unquote

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import sync_to_async
from django.db import close_old_connections
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User

from .realtime import workshop_group_name


@sync_to_async(thread_sensitive=False)
def user_from_access_token(raw_token):
    close_old_connections()
    try:
        try:
            token = AccessToken(raw_token)
            user_id = token["user_id"]
        except (KeyError, TokenError):
            return None
        return User.objects.select_related("workshop").filter(pk=user_id, is_active=True, workshop__isnull=False).first()
    finally:
        close_old_connections()


class WorkshopUpdatesConsumer(AsyncJsonWebsocketConsumer):
    """Authenticated, workshop-only hints that tell mobile clients to refresh."""

    async def connect(self):
        token_protocol = next((item for item in self.scope.get("subprotocols", []) if item.startswith("jwt.")), None)
        if token_protocol is None:
            await self.close(code=4401)
            return
        user = await user_from_access_token(unquote(token_protocol[4:]))
        if user is None:
            await self.close(code=4401)
            return
        self.group_name = workshop_group_name(user.workshop_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept(subprotocol="azm")

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def workshop_update(self, event):
        await self.send_json({
            "type": "workshop.update",
            "entity": event["entity"],
            "record_id": event["record_id"],
            "job_card_id": event.get("job_card_id"),
        })
