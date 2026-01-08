# apps/appointments/serializers.py
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from medismile.utils.auth import resolve_request_user

from apps.accounts.models import User, Role
from apps.cases.models import Case, CaseHistory
from .models import Appointment
from django.utils import timezone


# ============================================================
# Helpers
# ============================================================
def _check_conflicts(*, scheduled_at, duration_minutes, patient_id, student_id=None, supervisor_id=None, appointment_id=None):
    """
    Reject overlapping appointments for patient/student/supervisor on active slots.
    """
    end_at = scheduled_at + timezone.timedelta(minutes=duration_minutes)
    qs = Appointment.objects.filter(status__in=[Appointment.Status.SCHEDULED, Appointment.Status.RESCHEDULED])
    if appointment_id:
        qs = qs.exclude(id=appointment_id)

    def overlaps(appt):
        appt_end = appt.scheduled_at + timezone.timedelta(minutes=appt.duration_minutes or 0)
        return appt.scheduled_at < end_at and scheduled_at < appt_end

    # collect minimal set
    related = []
    if patient_id:
        related.extend(list(qs.filter(patient_id=patient_id)))
    if student_id:
        related.extend(list(qs.filter(student_id=student_id)))
    if supervisor_id:
        related.extend(list(qs.filter(supervisor_id=supervisor_id)))

    for appt in related:
        if overlaps(appt):
            raise serializers.ValidationError(_("Scheduling conflict detected."))


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
            "scheduled_at",
            "duration_minutes",
            "location",
            "telehealth_link",
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
    - Patient cannot create
    - Student creates for assigned case
    - Supervisor can create only for cases he supervises (exception)
    """

    case_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Appointment
        fields = (
            "case_id",
            "scheduled_at",
            "duration_minutes",
            "location",
            "telehealth_link",
            "is_follow_up",
            "notes",
        )

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

        if case.status not in {Case.Status.ACCEPTED, Case.Status.ASSIGNED, Case.Status.IN_PROGRESS}:
            raise serializers.ValidationError(_("Appointment cannot be created for this case status."))

        if role_name == Role.STUDENT:
            if not case.student_id or case.student_id != actor.id:
                raise serializers.ValidationError(_("You are not assigned to this case."))
            attrs["student"] = actor
        else:
            attrs["student"] = case.student

        if role_name == Role.SUPERVISOR and case.supervisor_id != actor.id:
            raise serializers.ValidationError(_("You are not supervising this case."))

        scheduled_at = attrs.get("scheduled_at")
        duration = attrs.get("duration_minutes") or 30
        _check_conflicts(
            scheduled_at=scheduled_at,
            duration_minutes=duration,
            patient_id=case.patient_id,
            student_id=attrs.get("student").id if attrs.get("student") else None,
            supervisor_id=case.supervisor_id,
        )

        attrs["case"] = case
        attrs["patient"] = case.patient
        attrs["supervisor"] = case.supervisor
        attrs["created_by"] = actor

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("case_id", None)
        appointment = Appointment.objects.create(**validated_data)
        CaseHistory.objects.create(
            case=appointment.case,
            action=CaseHistory.Action.STATUS_CHANGED,
            description=_("Appointment created."),
            performed_by=validated_data.get("created_by"),
        )
        return appointment


class AppointmentUpdateSerializer(serializers.ModelSerializer):
    """
    Update appointment (notes/reschedule). Status terminal changes handled by action endpoints.
    """

    class Meta:
        model = Appointment
        fields = (
            "scheduled_at",
            "duration_minutes",
            "location",
            "telehealth_link",
            "status",
            "notes",
            "is_archived",
        )

    def validate(self, attrs):
        request = self.context.get("request")
        actor = resolve_request_user(request)
        instance: Appointment = self.instance

        if not actor:
            raise serializers.ValidationError(_("Authentication required."))

        role_name = getattr(actor.role, "name", None)

        if role_name == Role.PATIENT:
            raise serializers.ValidationError(_("Patients are not allowed to modify appointments."))

        if instance.status in {Appointment.Status.COMPLETED, Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW}:
            raise serializers.ValidationError(_("Completed/cancelled/no-show appointments cannot be modified."))

        if role_name == Role.STUDENT:
            if instance.student_id != actor.id:
                raise serializers.ValidationError(_("You are not assigned to this appointment."))

        if role_name == Role.SUPERVISOR:
            if instance.supervisor_id != actor.id:
                raise serializers.ValidationError(_("You are not supervising this appointment."))

        schedule_changed = any(field in attrs for field in ("scheduled_at", "duration_minutes", "location", "telehealth_link"))
        if "status" in attrs:
            raise serializers.ValidationError(_("Use dedicated endpoints to change appointment status."))

        if schedule_changed:
            scheduled_at = attrs.get("scheduled_at", instance.scheduled_at)
            duration = attrs.get("duration_minutes", instance.duration_minutes)
            _check_conflicts(
                scheduled_at=scheduled_at,
                duration_minutes=duration,
                patient_id=instance.patient_id,
                student_id=instance.student_id,
                supervisor_id=instance.supervisor_id,
                appointment_id=instance.id,
            )

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        schedule_changed = any(field in validated_data for field in ("scheduled_at", "duration_minutes", "location", "telehealth_link"))

        for field in ("scheduled_at", "duration_minutes", "location", "telehealth_link", "notes", "is_archived"):
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        if schedule_changed:
            instance.status = Appointment.Status.RESCHEDULED

        instance.save()

        CaseHistory.objects.create(
            case=instance.case,
            action=CaseHistory.Action.STATUS_CHANGED,
            description=("Appointment rescheduled." if schedule_changed else "Appointment updated."),
            performed_by=resolve_request_user(self.context.get("request")),
        )
        return instance


# ============================================================
# Action Serializers (Reschedule / Cancel / Complete)
# ============================================================

class AppointmentRescheduleSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(required=False, min_value=1)
    location = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    telehealth_link = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        appointment: Appointment = self.context["appointment"]
        actor = resolve_request_user(self.context.get("request"))
        if appointment.status in {Appointment.Status.COMPLETED, Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW}:
            raise serializers.ValidationError(_("Cannot reschedule a completed/cancelled/no-show appointment."))
        scheduled_at = attrs["scheduled_at"]
        duration = attrs.get("duration_minutes") or appointment.duration_minutes
        _check_conflicts(
            scheduled_at=scheduled_at,
            duration_minutes=duration,
            patient_id=appointment.patient_id,
            student_id=appointment.student_id,
            supervisor_id=appointment.supervisor_id,
            appointment_id=appointment.id,
        )
        attrs["duration_minutes"] = duration
        attrs["actor"] = actor
        return attrs


class AppointmentCancelSerializer(serializers.Serializer):
    reason = serializers.CharField()


class AppointmentCompleteSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=[Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW])
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
