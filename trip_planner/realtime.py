"""
Helpers to broadcast live updates via Channels.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_notification(title: str, message: str, variant: str = "info", **extra):
    """Broadcast a notification to all connected WebSocket clients."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "spotter_live_updates",
        {
            "type": "broadcast_notification",
            "payload": {
                "title": title,
                "message": message,
                "variant": variant,
                **extra,
            },
        },
    )


def broadcast_driver_location(driver_id: str, trip_id: str, lat: float, lng: float, **extra):
    """Broadcast driver location update."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "spotter_live_updates",
        {
            "type": "broadcast_driver_location",
            "payload": {
                "driver_id": driver_id,
                "trip_id": trip_id,
                "lat": lat,
                "lng": lng,
                **extra,
            },
        },
    )


def broadcast_trip_update(trip_id: str, status: str, **extra):
    """Broadcast trip status update."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "spotter_live_updates",
        {
            "type": "broadcast_trip_update",
            "payload": {
                "trip_id": trip_id,
                "status": status,
                **extra,
            },
        },
    )
