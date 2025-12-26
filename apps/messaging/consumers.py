# apps/messaging/consumers.py
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from django.contrib.auth import get_user_model

from .models import Room, Message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for case-based chat.
    """

    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        allowed = await self.user_can_access_room()
        if not allowed:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get("content")

        if not content:
            return

        message = await self.create_message(content)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": {
                    "id": str(message.id),
                    "sender": self.user.email,
                    "content": message.content,
                    "sent_at": message.sent_at.isoformat(),
                },
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    # =====================================================
    # DB helpers
    # =====================================================
    @database_sync_to_async
    def user_can_access_room(self) -> bool:
        try:
            room = Room.objects.select_related(
                "case", "participant1", "participant2"
            ).get(id=self.room_id)
        except Room.DoesNotExist:
            return False

        return self.user in [room.participant1, room.participant2]

    @database_sync_to_async
    def create_message(self, content: str) -> Message:
        room = Room.objects.get(id=self.room_id)
        return Message.objects.create(
            room=room,
            sender=self.user,
            content=content,
        )
