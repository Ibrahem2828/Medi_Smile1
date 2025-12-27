# apps/messaging/consumers.py
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from django.contrib.auth import get_user_model

from apps.accounts.models import Role
from apps.audit.services import log_audit_event
from .models import Room, Message
from .permissions import (
    is_case_participant,
    is_university_admin_for_case,
    is_case_chat_open,
)

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
            await self._log_ws_event("messaging.ws.denied", "Unauthenticated websocket access")
            await self.close()
            return

        allowed = await self.user_can_access_room()
        if not allowed:
            await self._log_ws_event("messaging.ws.denied", "Unauthorized websocket access")
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self._log_ws_event("messaging.ws.connected", "Websocket connected")
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

        can_send = await self.user_can_send_message()
        if not can_send:
            await self._log_ws_event("messaging.ws.send_denied", "User not allowed to send message")
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
                "case",
                "participant_patient",
                "participant_student",
            ).get(id=self.room_id)
        except Room.DoesNotExist:
            return False

        user = self.user
        role = getattr(user, "role_name", None)
        case = room.case

        if role == Role.TECH_SUPPORT:
            return True

        if role in {Role.PATIENT, Role.STUDENT, Role.SUPERVISOR}:
            return is_case_participant(user, case)

        if role == Role.UNIVERSITY_ADMIN:
            return is_university_admin_for_case(user, case)

        return False

    @database_sync_to_async
    def user_can_send_message(self) -> bool:
        try:
            room = Room.objects.select_related(
                "case",
                "participant_patient",
                "participant_student",
            ).get(id=self.room_id)
        except Room.DoesNotExist:
            return False

        user = self.user
        role = getattr(user, "role_name", None)

        if role not in {Role.PATIENT, Role.STUDENT}:
            return False

        if not is_case_chat_open(room.case):
            return False

        return user in {room.participant_patient, room.participant_student}

    @database_sync_to_async
    def create_message(self, content: str) -> Message:
        room = Room.objects.get(id=self.room_id)
        msg = Message.objects.create(
            room=room,
            sender=self.user,
            content=content.strip(),
        )
        log_audit_event(
            user=self.user,
            university=room.case.university,
            action="messaging.message.sent.ws",
            description="Message sent via websocket",
            content_object=msg,
            metadata={
                "room_id": str(room.id),
                "case_id": str(room.case_id),
            },
        )
        return msg

    @database_sync_to_async
    def _log_ws_event(self, action: str, description: str):
        try:
            room = Room.objects.select_related("case").filter(id=self.room_id).first()
            university = room.case.university if room else None
        except Exception:
            room = None
            university = None
        log_audit_event(
            user=self.user if getattr(self.user, "is_authenticated", False) else None,
            university=university,
            action=action,
            description=description,
            content_object=room,
            metadata={"room_id": self.room_id},
        )
