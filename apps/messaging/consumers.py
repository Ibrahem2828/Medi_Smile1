# apps/messaging/consumers.py
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from django.contrib.auth import get_user_model

from apps.accounts.models import Role
from apps.audit.services import log_audit_event
from .models import Room, Message
from .permissions import (
    is_case_participant,
    is_university_admin_for_room,
    is_room_chat_open,
)

User = get_user_model()
logger = logging.getLogger(__name__)


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
        room_group_name = getattr(self, "room_group_name", None)
        if not room_group_name:
            return

        try:
            await self.channel_layer.group_discard(room_group_name, self.channel_name)
        except Exception:
            logger.exception("WebSocket group discard failed")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (TypeError, json.JSONDecodeError):
            logger.warning("Rejected malformed WebSocket message")
            return

        if not isinstance(data, dict):
            logger.warning("Rejected non-object WebSocket message")
            return

        content = data.get("content")

        if not isinstance(content, str) or not content.strip():
            return

        try:
            can_send = await self.user_can_send_message()
        except Exception:
            logger.exception("WebSocket message authorization failed")
            return

        if not can_send:
            await self._log_ws_event("messaging.ws.send_denied", "User not allowed to send message")
            return

        try:
            message = await self.create_message(content)
        except Exception:
            logger.exception("WebSocket message creation failed")
            return

        try:
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
        except Exception:
            logger.exception("WebSocket message broadcast failed")

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
                "course",
                "participant_patient",
                "participant_student",
                "participant_supervisor",
            ).get(id=self.room_id)
        except Room.DoesNotExist:
            return False

        user = self.user
        role = getattr(user, "role_name", None) or getattr(getattr(user, "role", None), "name", None)
        case = room.case

        if role == Role.TECH_SUPPORT:
            return True

        if room.thread_type == Room.ThreadType.COURSE:
            if role in {Role.STUDENT, Role.SUPERVISOR}:
                return user in {room.participant_student, room.participant_supervisor}
            if role == Role.UNIVERSITY_ADMIN:
                return is_university_admin_for_room(user, room)
            return False

        if role in {Role.PATIENT, Role.STUDENT, Role.SUPERVISOR}:
            return is_case_participant(user, case)

        if role == Role.UNIVERSITY_ADMIN:
            return is_university_admin_for_room(user, room)

        return False

    @database_sync_to_async
    def user_can_send_message(self) -> bool:
        try:
            room = Room.objects.select_related(
                "case",
                "course",
                "participant_patient",
                "participant_student",
                "participant_supervisor",
            ).get(id=self.room_id)
        except Room.DoesNotExist:
            return False

        user = self.user
        role = getattr(user, "role_name", None) or getattr(getattr(user, "role", None), "name", None)

        if not is_room_chat_open(room):
            return False

        if room.thread_type == Room.ThreadType.COURSE:
            if role not in {Role.STUDENT, Role.SUPERVISOR}:
                return False
            return user in {room.participant_student, room.participant_supervisor}

        if role not in {Role.PATIENT, Role.STUDENT}:
            return False

        return user in {room.participant_patient, room.participant_student}

    @database_sync_to_async
    def create_message(self, content: str) -> Message:
        room = Room.objects.select_related("case", "course").get(id=self.room_id)
        msg = Message.objects.create(
            room=room,
            sender=self.user,
            content=content.strip(),
        )
        university = room.case.university if room.case_id else room.course.university
        log_audit_event(
            user=self.user,
            university=university,
            action="messaging.message.sent.ws",
            description="Message sent via websocket",
            content_object=msg,
            metadata={
                "room_id": str(room.id),
                "case_id": str(room.case_id) if room.case_id else None,
                "course_id": str(room.course_id) if room.course_id else None,
            },
        )
        return msg

    @database_sync_to_async
    def _log_ws_event(self, action: str, description: str):
        try:
            room = Room.objects.select_related("case", "course").filter(id=self.room_id).first()
            university = None
            if room:
                university = room.case.university if room.case_id else room.course.university
        except Exception:
            room = None
            university = None
        try:
            log_audit_event(
                user=self.user if getattr(self.user, "is_authenticated", False) else None,
                university=university,
                action=action,
                description=description,
                content_object=room,
                metadata={"room_id": self.room_id},
            )
        except Exception:
            logger.exception("WebSocket audit logging failed")
