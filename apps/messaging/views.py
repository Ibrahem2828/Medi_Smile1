# apps/messaging/views.py
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Role
from apps.cases.models import Case

from .models import Room, Message
from .serializers import RoomSerializer, MessageSerializer
from .permissions import (
    IsAuthenticatedAndActive,
    CanViewRoom,
    CanCreateRoom,
    CanSendMessage,
    CanViewMessage,
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
        "participant1",
        "participant2",
    )

    serializer_class = RoomSerializer
    permission_classes = [
        IsAuthenticatedAndActive,
        CanViewRoom,
    ]


class RoomCreateView(generics.CreateAPIView):
    """
    Create (or get) room for a case.
    One room per case.
    """
    serializer_class = RoomSerializer
    permission_classes = [
        IsAuthenticatedAndActive,
        CanCreateRoom,
    ]

    def perform_create(self, serializer):
        case = serializer.validated_data["case"]

        room, _ = Room.objects.get_or_create(
            case=case,
            defaults={
                "participant1": case.patient,
                "participant2": case.student,
            },
        )

        serializer.instance = room


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
    ]

    def get_queryset(self):
        room_id = self.kwargs["room_id"]
        room = Room.objects.select_related("case").get(id=room_id)

        if not CanViewRoom().has_object_permission(self.request, self, room):
            raise PermissionDenied("You cannot access this conversation")

        return Message.objects.filter(room=room).select_related("sender")

    def perform_create(self, serializer):
        room_id = self.kwargs["room_id"]
        room = Room.objects.get(id=room_id)

        if not CanSendMessage().has_object_permission(self.request, self, room):
            raise PermissionDenied("You cannot send messages here")

        serializer.save(room=room)


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
        CanViewMessage,
    ]
