"""
WebSocket URL routing.
Channels URLRouter strips leading slash; path is e.g. 'ws/live/'.
"""

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/live/", consumers.LiveUpdatesConsumer.as_asgi()),
]
