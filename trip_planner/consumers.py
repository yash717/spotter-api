"""
WebSocket consumers for live updates: driver location, trip status, notifications.
"""

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class LiveUpdatesConsumer(AsyncJsonWebsocketConsumer):
    """Handles live driver location, trip status, and notifications."""

    async def connect(self):
        self.room_name = "live_updates"
        self.room_group_name = f"spotter_{self.room_name}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connected", "channel": self.room_group_name})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content):
        """Handle incoming messages (e.g. driver location from mobile)."""
        msg_type = content.get("type", "unknown")
        if msg_type == "ping":
            await self.send_json({"type": "pong"})
        elif msg_type == "driver_location":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "broadcast.driver_location", "payload": content},
            )
        elif msg_type == "trip_update":
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "broadcast.trip_update", "payload": content},
            )

    async def broadcast_driver_location(self, event):
        await self.send_json({"type": "driver_location", "data": event["payload"]})

    async def broadcast_trip_update(self, event):
        await self.send_json({"type": "trip_update", "data": event["payload"]})

    async def broadcast_notification(self, event):
        await self.send_json({"type": "notification", "data": event["payload"]})
