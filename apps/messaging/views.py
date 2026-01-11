# apps/messaging/views.py
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db import models

from apps.accounts.models import Role
from apps.cases.models import Case
from apps.universities.models import Course
from medismile.permissions import MatrixPermission
from apps.audit.services import log_audit_event

from .models import Room, Message
from .serializers import RoomSerializer, MessageSerializer, RoomCreateSerializer
from .permissions import (
    IsAuthenticatedAndActive,
    CanViewRoom,
    CanViewMessage,
    is_course_participant,
    is_university_admin_for_room,
    is_room_chat_open,
)


# ============================================================
# Room Views
# ============================================================
class RoomCreateMixin:
    def _create_room(self, serializer):
        data = serializer.validated_data
        thread_type = data.get("thread_type") or Room.ThreadType.CASE
        user = self.request.user

        if thread_type == Room.ThreadType.CASE:
            case = data["case"]

            if not case.student_id:
                raise PermissionDenied("Case must be assigned to a student before opening chat.")

            if user not in {case.patient, case.student}:
                raise PermissionDenied("You are not assigned to this case.")

            if case.status not in {
                Case.Status.ASSIGNED,
                Case.Status.IN_PROGRESS,
            }:
                raise PermissionDenied("Chat is only available for assigned / in-progress cases.")

            self.permission_object = case
            self.check_object_permissions(self.request, case)

            with transaction.atomic():
                room, created = Room.objects.select_for_update().get_or_create(
                    case=case,
                    defaults={
                        "thread_type": Room.ThreadType.CASE,
                        "participant_patient": case.patient,
                        "participant_student": case.student,
                    },
                )

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

            return room

        course = data["course"]
        student = data["participant_student"]
        supervisor = data["participant_supervisor"]

        if user not in {student, supervisor}:
            raise PermissionDenied("You are not assigned to this course thread.")

        self.permission_object = course
        self.check_object_permissions(self.request, course)

        with transaction.atomic():
            room, created = Room.objects.select_for_update().get_or_create(
                thread_type=Room.ThreadType.COURSE,
                course=course,
                participant_student=student,
                participant_supervisor=supervisor,
                defaults={
                    "participant_student": student,
                    "participant_supervisor": supervisor,
                },
            )

        log_audit_event(
            user=user,
            university=course.university,
            action="messaging.room.created" if created else "messaging.room.retrieved",
            description="Room opened for course chat",
            content_object=course,
            metadata={
                "room_id": str(room.id),
                "course_id": str(course.id),
                "created": created,
            },
        )

        return room


class ThreadListCreateView(RoomCreateMixin, generics.ListCreateAPIView):
    """
    List accessible rooms for the authenticated user.
    """
    serializer_class = RoomSerializer
    permission_classes = [
        IsAuthenticatedAndActive,
        MatrixPermission,
    ]
    permission_resource = "messaging.room"
    permission_ownership_checker = staticmethod(
        lambda user, obj: (
            CanViewRoom().has_object_permission(  # type: ignore
                type("req", (), {"user": user})(), None, obj
            )
            if isinstance(obj, Room)
            else (
                (isinstance(obj, Case) and user in {obj.patient, obj.student})
                or (isinstance(obj, Course) and is_course_participant(user, obj))
            )
        )
    )
    permission_state_checker = staticmethod(lambda obj: is_room_chat_open(obj))  # type: ignore

    def get_queryset(self):
        user = self.request.user
        role_name = getattr(user, "role_name", None) or getattr(getattr(user, "role", None), "name", None)
        qs = Room.objects.select_related(
            "case",
            "course",
            "participant_patient",
            "participant_student",
            "participant_supervisor",
        )

        if role_name == Role.TECH_SUPPORT:
            return qs
        if role_name == Role.PATIENT:
            return qs.filter(participant_patient=user)
        if role_name == Role.STUDENT:
            return qs.filter(participant_student=user)
        if role_name == Role.SUPERVISOR:
            return qs.filter(models.Q(case__supervisor=user) | models.Q(participant_supervisor=user))
        if role_name == Role.UNIVERSITY_ADMIN:
            university_id = getattr(getattr(user, "universityadminprofile_profile", None), "university_id", None)
            return qs.filter(
                models.Q(case__university_id=university_id) | models.Q(course__university_id=university_id)
            )
        return Room.objects.none()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return RoomCreateSerializer
        return RoomSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = self._create_room(serializer)
        output = RoomSerializer(room, context={"request": request}).data
        return Response(output, status=status.HTTP_201_CREATED)


class RoomRetrieveView(generics.RetrieveAPIView):
    """
    Retrieve conversation room for a case.
    """
    queryset = Room.objects.select_related(
        "case",
        "course",
        "participant_patient",
        "participant_student",
        "participant_supervisor",
    )

    serializer_class = RoomSerializer
    permission_classes = [
        IsAuthenticatedAndActive,
        MatrixPermission,
    ]
    permission_resource = "messaging.room"
    permission_action = "view"
    permission_ownership_checker = staticmethod(
        lambda user, room: CanViewRoom().has_object_permission(  # type: ignore
            type("req", (), {"user": user})(), None, room
        )
    )


class RoomCreateView(RoomCreateMixin, generics.CreateAPIView):
    """
    Create (or get) room for a case or course.
    One room per case, one per course/student pair.
    """
    serializer_class = RoomCreateSerializer
    permission_classes = [
        IsAuthenticatedAndActive,
        MatrixPermission,
    ]
    permission_resource = "messaging.room"
    permission_action = "create"
    permission_ownership_checker = staticmethod(
        lambda user, obj: (
            (isinstance(obj, Case) and user in {obj.patient, obj.student})
            or (isinstance(obj, Course) and is_course_participant(user, obj))
        )
    )
    permission_state_checker = staticmethod(lambda obj: is_room_chat_open(obj))  # type: ignore

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = self._create_room(serializer)
        output = RoomSerializer(room, context={"request": request}).data
        return Response(output, status=status.HTTP_201_CREATED)


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
    permission_ownership_checker = staticmethod(
        lambda user, obj: CanViewRoom().has_object_permission(  # type: ignore
            type("req", (), {"user": user})(), None, obj if isinstance(obj, Room) else obj.room  # type: ignore
        )
    )
    permission_scope_checker = staticmethod(
        lambda user, obj: (
            True
            if getattr(user, "role_name", None) != Role.UNIVERSITY_ADMIN
            else is_university_admin_for_room(  # type: ignore
                user, obj if isinstance(obj, Room) else obj.room  # type: ignore
            )
        )
    )
    permission_state_checker = staticmethod(
        lambda obj: is_room_chat_open(obj if isinstance(obj, Room) else obj.room)  # type: ignore
    )

    def get_queryset(self):
        room_id = self.kwargs["room_id"]
        room = get_object_or_404(
            Room.objects.select_related(
                "case",
                "course",
                "participant_patient",
                "participant_student",
                "participant_supervisor",
            ),
            id=room_id,
        )

        self.check_object_permissions(self.request, room)

        return Message.objects.filter(room=room).select_related("sender")

    def perform_create(self, serializer):
        room_id = self.kwargs["room_id"]
        room = get_object_or_404(
            Room.objects.select_related("case", "course"),
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

        university = room.case.university if room.case_id else room.course.university
        log_audit_event(
            user=self.request.user,
            university=university,
            action="messaging.message.sent",
            description="Message sent in room",
            content_object=message,
            metadata={
                "room_id": str(room.id),
                "case_id": str(room.case_id) if room.case_id else None,
                "course_id": str(room.course_id) if room.course_id else None,
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
        "room__course",
        "sender",
    )
    serializer_class = MessageSerializer
    permission_classes = [
        IsAuthenticatedAndActive,
        MatrixPermission,
    ]
    permission_resource = "messaging.message"
    permission_action = "view"
    permission_ownership_checker = staticmethod(
        lambda user, message: CanViewMessage().has_object_permission(  # type: ignore
            type("req", (), {"user": user})(), None, message
        )
    )
    permission_scope_checker = staticmethod(
        lambda user, message: (
            True
            if getattr(user, "role_name", None) != Role.UNIVERSITY_ADMIN
            else is_university_admin_for_room(user, message.room)  # type: ignore
        )
    )
