from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.accounts.models import Role
from apps.cases.models import Case
from apps.universities.models import Course
from .models import Room, Message

User = get_user_model()


# ============================================================
# Minimal Public User Serializer (Messaging Scope)
# ============================================================
class MessagingUserSerializer(serializers.ModelSerializer):
    """
    Minimal, read-only user representation for messaging.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
        )
        read_only_fields = fields


# ============================================================
# Message Serializer
# ============================================================
class MessageSerializer(serializers.ModelSerializer):
    sender = MessagingUserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "sender",
            "content",
            "sent_at",
            "is_system",
        )
        read_only_fields = (
            "id",
            "sender",
            "sent_at",
            "is_system",
        )

    def validate_content(self, value: str) -> str:
        if not value or not value.strip():
            raise serializers.ValidationError("Message content cannot be empty.")
        return value.strip()


# ============================================================
# Room Serializer
# ============================================================
class RoomSerializer(serializers.ModelSerializer):
    thread_type = serializers.CharField(read_only=True)
    case = serializers.PrimaryKeyRelatedField(read_only=True)
    case_id = serializers.UUIDField(source="case.id", read_only=True)
    course = serializers.PrimaryKeyRelatedField(read_only=True)
    course_id = serializers.UUIDField(source="course.id", read_only=True)
    participant_patient = MessagingUserSerializer(read_only=True)
    participant_student = MessagingUserSerializer(read_only=True)
    participant_supervisor = MessagingUserSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = (
            "id",
            "thread_type",
            "case",
            "case_id",
            "course",
            "course_id",
            "participant_patient",
            "participant_student",
            "participant_supervisor",
            "created_at",
            "messages",
        )
        read_only_fields = (
            "id",
            "thread_type",
            "participant_patient",
            "participant_student",
            "participant_supervisor",
            "created_at",
            "messages",
        )


class RoomCreateSerializer(serializers.Serializer):
    thread_type = serializers.ChoiceField(choices=Room.ThreadType.choices, default=Room.ThreadType.CASE)
    case_id = serializers.UUIDField(required=False)
    case = serializers.UUIDField(required=False)
    course_id = serializers.UUIDField(required=False)
    student_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        role_name = getattr(getattr(user, "role", None), "name", None)

        thread_type = attrs.get("thread_type") or Room.ThreadType.CASE

        if thread_type == Room.ThreadType.CASE:
            case_id = attrs.get("case_id") or attrs.get("case")
            if not case_id:
                raise serializers.ValidationError({"case_id": "case_id is required for case threads."})
            case = Case.objects.select_related(
                "patient",
                "student",
                "supervisor",
                "university",
            ).filter(id=case_id).first()
            if not case:
                raise serializers.ValidationError({"case_id": "Case not found."})
            if not case.patient_id or not case.student_id:
                raise serializers.ValidationError("Case must have both patient and assigned student.")
            if case.status not in {
                Case.Status.ASSIGNED,
                Case.Status.IN_PROGRESS,
            }:
                raise serializers.ValidationError("Chat is available only for assigned / in-progress cases.")
            if role_name not in {Role.PATIENT, Role.STUDENT} or user not in {case.patient, case.student}:
                raise serializers.ValidationError("You are not allowed to open this case thread.")
            attrs["case"] = case
            attrs["course"] = None
            attrs["participant_student"] = case.student
            attrs["participant_patient"] = case.patient
            return attrs

        if thread_type == Room.ThreadType.COURSE:
            course_id = attrs.get("course_id")
            if not course_id:
                raise serializers.ValidationError({"course_id": "course_id is required for course threads."})
            course = Course.objects.select_related("supervisor", "university").filter(id=course_id, is_active=True).first()
            if not course:
                raise serializers.ValidationError({"course_id": "Course not found or inactive."})
            if not course.supervisor_id:
                raise serializers.ValidationError({"course_id": "Course must have an assigned supervisor."})

            if role_name == Role.STUDENT:
                if not course.students.filter(id=user.id).exists():
                    raise serializers.ValidationError("You are not enrolled in this course.")
                attrs["participant_student"] = user
                attrs["participant_supervisor"] = course.supervisor

            elif role_name == Role.SUPERVISOR:
                if course.supervisor_id != user.id:
                    raise serializers.ValidationError("You are not the supervisor of this course.")
                student_id = attrs.get("student_id")
                if not student_id:
                    raise serializers.ValidationError({"student_id": "student_id is required for supervisors."})
                student = User.objects.filter(id=student_id, role__name=Role.STUDENT).first()
                if not student or not course.students.filter(id=student.id).exists():
                    raise serializers.ValidationError({"student_id": "Student not enrolled in this course."})
                attrs["participant_student"] = student
                attrs["participant_supervisor"] = user

            else:
                raise serializers.ValidationError("Only students or supervisors can open course threads.")

            attrs["course"] = course
            attrs["case"] = None
            return attrs

        raise serializers.ValidationError({"thread_type": "Invalid thread type."})
