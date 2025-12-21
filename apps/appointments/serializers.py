# apps/appointments/serializers.py

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from apps.accounts.serializers import UserSerializer
from apps.cases.serializers import CaseSerializer
from apps.cases.models import Case
from medismile.utils.auth import resolve_request_user

from .models import Appointment


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
    - admin / IT
    """

    patient = UserSerializer(read_only=True)
    student = UserSerializer(read_only=True)
    supervisor = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    case = CaseSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = [
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
        ]
        read_only_fields = fields


# ============================================================
# Create Serializer
# ============================================================

class AppointmentCreateSerializer(serializers.ModelSerializer):
    """
    Create appointment serializer.

    Business Rules:
    - ❌ Patient cannot create appointments
    - ✅ Student creates appointment for assigned case
    - ⚠ Supervisor can create only in exceptional cases
    - Appointment MUST belong to an assigned case
    """

    case_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Appointment
        fields = [
            "case_id",
            "appointment_date",
            "is_follow_up",
            "notes",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        actor = resolve_request_user(request)

        if not actor:
            raise serializers.ValidationError(_("Authentication required."))

        if actor.role not in ["student", "supervisor"]:
            raise serializers.ValidationError(
                _("Only students or supervisors can create appointments.")
            )

        case_id = attrs.get("case_id")

        try:
            case = (
                Case.objects
                .select_related("patient", "student", "supervisor")
                .get(id=case_id)
            )
        except Case.DoesNotExist:
            raise serializers.ValidationError({"case_id": _("Case not found.")})

        # Case must be assigned
        if not case.student:
            raise serializers.ValidationError(
                _("Appointment cannot be created before case assignment.")
            )

        # Student rules
        if actor.role == "student" and case.student != actor:
            raise serializers.ValidationError(
                _("You are not assigned to this case.")
            )

        # Supervisor rules
        if actor.role == "supervisor" and case.supervisor != actor:
            raise serializers.ValidationError(
                _("You are not supervising this case.")
            )

        attrs["case"] = case
        attrs["patient"] = case.patient
        attrs["student"] = case.student
        attrs["supervisor"] = case.supervisor
        attrs["created_by"] = actor

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("case_id", None)
        return Appointment.objects.create(**validated_data)


# ============================================================
# Update Serializer
# ============================================================

class AppointmentUpdateSerializer(serializers.ModelSerializer):
    """
    Update appointment serializer.

    Permissions:
    - ❌ Patient: no updates
    - ✅ Student:
        - update date
        - update status (limited)
        - add notes
    - ✅ Supervisor:
        - update status only
    """

    class Meta:
        model = Appointment
        fields = [
            "appointment_date",
            "status",
            "notes",
            "is_archived",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        actor = resolve_request_user(request)
        instance: Appointment = self.instance

        if not actor:
            raise serializers.ValidationError(_("Authentication required."))

        if actor.role == "patient":
            raise serializers.ValidationError(
                _("Patients are not allowed to modify appointments.")
            )

        # Student permissions
        if actor.role == "student":
            if instance.student != actor:
                raise serializers.ValidationError(
                    _("You are not assigned to this appointment.")
                )

        # Supervisor permissions
        if actor.role == "supervisor":
            if instance.supervisor != actor:
                raise serializers.ValidationError(
                    _("You are not supervising this appointment.")
                )

            # Supervisor can only change status
            forbidden = {"appointment_date", "notes", "is_archived"}
            if forbidden.intersection(attrs.keys()):
                raise serializers.ValidationError(
                    _("Supervisors can only update appointment status.")
                )

        # Immutable statuses
        if instance.status in {
            Appointment.Status.COMPLETED,
            Appointment.Status.CANCELLED,
            Appointment.Status.NO_SHOW,
        }:
            raise serializers.ValidationError(
                _("Completed or cancelled appointments cannot be modified.")
            )

        return attrs
