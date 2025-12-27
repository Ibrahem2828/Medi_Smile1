# apps/messaging/views.py
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.throttling import ScopedRateThrottle
from django.shortcuts import get_object_or_404
from django.db import transaction

from apps.accounts.models import Role
from apps.cases.models import Case
from medismile.permissions import MatrixPermission
from apps.audit.services import log_audit_event

from .models import Room, Message
from .serializers import RoomSerializer, MessageSerializer
from .permissions import (
    IsAuthenticatedAndActive,
    CanViewRoom,
    CanViewMessage,
    is_university_admin_for_case,
    is_case_chat_open,
)


# ============================================================
# Room Views
# ============================================================
class RoomRetrieveView(generics.RetrieveAPIView):
    """
    Retrieve conversation room for a case.
    """
    queryset = Room.objects.select_related(
        "case",
        "participant_patient",
        "participant_student",
    )

    serializer_class = RoomSerializer
    permission_classes = [
        IsAuthenticatedAndActive,
        MatrixPermission,
    ]
    permission_resource = "messaging.room"
    permission_action = "view"
    permission_ownership_checker = (
        lambda user, room: CanViewRoom().has_object_permission(  # type: ignore
            type("req", (), {"user": user})(), None, room
        )
    )


class RoomCreateView(generics.CreateAPIView):
    """
    Create (or get) room for a case.
    One room per case.
    """
    serializer_class = RoomSerializer
    permission_classes = [
        IsAuthenticatedAndActive,
        MatrixPermission,
    ]
    permission_resource = "messaging.room"
    permission_action = "create"
    permission_ownership_checker = lambda user, case: user in {case.patient, case.student}  # type: ignore
    permission_state_checker = lambda case: is_case_chat_open(case)  # type: ignore

    def perform_create(self, serializer):
        case = serializer.validated_data["case"]
        user = self.request.user

        if not case.student_id:
            raise PermissionDenied("Case must be assigned to a student before opening chat.")

        if user not in {case.patient, case.student}:
            raise PermissionDenied("You are not assigned to this case.")

        if case.status not in {
            Case.Status.ASSIGNED,
            Case.Status.IN_PROGRESS,
        }:
            raise PermissionDenied("Chat is only available for assigned / in-progress cases.")

        # Object-level permission after serializer validation
        self.permission_object = case
        self.check_object_permissions(self.request, case)

        with transaction.atomic():
            room, created = Room.objects.select_for_update().get_or_create(
                case=case,
                defaults={
                    "participant_patient": case.patient,
                    "participant_student": case.student,
                },
            )

        serializer.instance = room

        log_audit_event(
            user=user,
            university=case.university,
            action="messaging.room.created" if created else "messaging.room.retrieved",
            description="Room opened for case chat",
            content_object=case,
            metadata={
                "room_id": str(room.id),
                "case_id": str(case.id),
                "created": created,
            },
        )


# ============================================================
# Message Views
# ============================================================
class MessageListCreateView(generics.ListCreateAPIView):
    """
    List & send messages in a room.
    """
    serializer_class = MessageSerializer
    permission_classes = [
        IsAuthenticatedAndActive,
        MatrixPermission,
    ]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "messaging"
    permission_resource = "messaging.message"
    permission_action = "view"
    permission_ownership_checker = (
        lambda user, obj: CanViewRoom().has_object_permission(  # type: ignore
            type("req", (), {"user": user})(), None, obj if isinstance(obj, Room) else obj.room  # type: ignore
        )
    )
    permission_scope_checker = (
        lambda user, obj: (
            True
            if getattr(user, "role_name", None) != Role.UNIVERSITY_ADMIN
            else is_university_admin_for_case(  # type: ignore
                user, obj.case if isinstance(obj, Room) else obj.room.case  # type: ignore
            )
        )
    )
    permission_state_checker = (
        lambda obj: is_case_chat_open(obj.case if isinstance(obj, Room) else obj.room.case)  # type: ignore
    )

    def get_queryset(self):
        room_id = self.kwargs["room_id"]
        room = get_object_or_404(
            Room.objects.select_related(
                "case",
                "participant_patient",
                "participant_student",
            ),
            id=room_id,
        )

        self.check_object_permissions(self.request, room)

        return Message.objects.filter(room=room).select_related("sender")

    def perform_create(self, serializer):
        room_id = self.kwargs["room_id"]
        room = get_object_or_404(
            Room.objects.select_related("case"),
            id=room_id,
        )

        # Switch permission action to "send" for create flow
        self.permission_action = "send"
        self.permission_object = room
        self.check_object_permissions(self.request, room)

        message = serializer.save(
            room=room,
            sender=self.request.user,
            is_system=False,
        )

        log_audit_event(
            user=self.request.user,
            university=room.case.university,
            action="messaging.message.sent",
            description="Message sent in room",
            content_object=message,
            metadata={
                "room_id": str(room.id),
                "case_id": str(room.case_id),
                "is_system": message.is_system,
            },
        )


class MessageDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single message (Audit / Read tracking).
    """
    queryset = Message.objects.select_related(
        "room",
        "room__case",
        "sender",
    )
    serializer_class = MessageSerializer
    permission_classes = [
        IsAuthenticatedAndActive,
        MatrixPermission,
    ]
    permission_resource = "messaging.message"
    permission_action = "view"
    permission_ownership_checker = (
        lambda user, message: CanViewMessage().has_object_permission(  # type: ignore
            type("req", (), {"user": user})(), None, message
        )
    )
    permission_scope_checker = (
        lambda user, message: (
            True
            if getattr(user, "role_name", None) != Role.UNIVERSITY_ADMIN
            else is_university_admin_for_case(user, message.room.case)  # type: ignore
        )
    )
