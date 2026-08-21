from django.urls import path

from .consumers import WorkshopUpdatesConsumer


websocket_urlpatterns = [
    path("ws/workshop/updates/", WorkshopUpdatesConsumer.as_asgi()),
]
