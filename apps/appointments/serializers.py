# apps/appointments/serializers.py
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from medismile.utils.auth import resolve_request_user

from apps.accounts.models import User, Role
from apps.cases.models import Case
from .models import Appointment


# ============================================================
# Local lightweight serializers (avoid cross-app tight coupling)
# ============================================================
class AppointmentUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role")
        read_only_fields = fields


class AppointmentCaseMiniSerializer(serializers.ModelSerializer):
    patient_id = serializers.UUIDField(source="patient.id", read_only=True)
    student_id = serializers.UUIDField(source="student.id", read_only=True)
    supervisor_id = serializers.UUIDField(source="supervisor.id", read_only=True)
    university_id = serializers.UUIDField(source="university.id", read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Case
        fields = ("id", "title", "status", "patient_id", "student_id", "supervisor_id", "university_id")
        read_only_fields = fields


# ============================================================
# Read Serializer (List / Detail)
# ============================================================
class AppointmentSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for appointments.
    Used by:
    - patient (read-only)
    - student
    - supervisor
    - university admin / IT (read)
    """

    patient = AppointmentUserSerializer(read_only=True)
    student = AppointmentUserSerializer(read_only=True)
    supervisor = AppointmentUserSerializer(read_only=True)
    created_by = AppointmentUserSerializer(read_only=True)
    case = AppointmentCaseMiniSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = (
            "id",
            "case",
            "patient",
            "student",
            "supervisor",
            "created_by",
            "appointment_date",
            "status",
            "is_follow_up",
            "notes",
            "is_archived",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


# ============================================================
# Create Serializer
# ============================================================
class AppointmentCreateSerializer(serializers.ModelSerializer):
    """
    Business Rules (per MediSmile):
    - ❌ Patient cannot create
    - ✅ Student creates for assigned case
    - ✅ Supervisor can create only for cases he supervises (exception)
    """

    case_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Appointment
        fields = ("case_id", "appointment_date", "is_follow_up", "notes")

    def validate(self, attrs):
        request = self.context.get("request")
        actor = resolve_request_user(request)

        if not actor:
            raise serializers.ValidationError(_("Authentication required."))

        role_name = getattr(actor.role, "name", None)
        if role_name not in {Role.STUDENT, Role.SUPERVISOR}:
            raise serializers.ValidationError(_("Only students or supervisors can create appointments."))

        case_id = attrs.get("case_id")
        try:
            case = Case.objects.select_related("patient", "student", "supervisor", "university").get(id=case_id)
        except Case.DoesNotExist:
            raise serializers.ValidationError({"case_id": _("Case not found.")})

        # Case must be assigned (student required)
        if not case.student_id:
            raise serializers.ValidationError(_("Appointment cannot be created before case assignment."))

        # Student rules
        if role_name == Role.STUDENT and case.student_id != actor.id:
            raise serializers.ValidationError(_("You are not assigned to this case."))

        # Supervisor rules
        if role_name == Role.SUPERVISOR and case.supervisor_id != actor.id:
            raise serializers.ValidationError(_("You are not supervising this case."))

        attrs["case"] = case
        attrs["patient"] = case.patient
        attrs["student"] = case.student
        attrs["supervisor"] = case.supervisor
        attrs["created_by"] = actor

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("case_id", None)
        appointment = Appointment.objects.create(**validated_data)
        return appointment


# ============================================================
# Update Serializer
# ============================================================
class AppointmentUpdateSerializer(serializers.ModelSerializer):
    """
    Update appointment serializer.

    Permissions (aligned with your scenario):
    - ❌ Patient: cannot update date/notes/status (he requests change via messaging)
    - ✅ Student:
        - update appointment_date
        - update notes
        - update status (limited by views/actions)
        - archive
    - ✅ Supervisor:
        - status only (limited)
    """

    class Meta:
        model = Appointment
        fields = ("appointment_date", "status", "notes", "is_archived")

    def validate(self, attrs):
        request = self.context.get("request")
        actor = resolve_request_user(request)
        instance: Appointment = self.instance

        if not actor:
            raise serializers.ValidationError(_("Authentication required."))

        role_name = getattr(actor.role, "name", None)

        if role_name == Role.PATIENT:
            raise serializers.ValidationError(_("Patients are not allowed to modify appointments."))

        # immutable final states
        if instance.status in {Appointment.Status.COMPLETED, Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW}:
            raise serializers.ValidationError(_("Completed/cancelled/no-show appointments cannot be modified."))

        # Student permissions
        if role_name == Role.STUDENT:
            if instance.student_id != actor.id:
                raise serializers.ValidationError(_("You are not assigned to this appointment."))

        # Supervisor permissions: status only
        if role_name == Role.SUPERVISOR:
            if instance.supervisor_id != actor.id:
                raise serializers.ValidationError(_("You are not supervising this appointment."))

            forbidden = {"appointment_date", "notes", "is_archived"}
            if forbidden.intersection(attrs.keys()):
                raise serializers.ValidationError(_("Supervisors can only update appointment status."))

        # Other roles disallowed
        if role_name not in {Role.STUDENT, Role.SUPERVISOR}:
            raise serializers.ValidationError(_("Not allowed."))

        return attrs
