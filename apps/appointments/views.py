# apps/appointments/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from apps.accounts.models import Role
from medismile.openapi import DetailMessage, success_envelope
from apps.cases.models import CaseHistory

from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    AppointmentCreateSerializer,
    AppointmentUpdateSerializer,
    AppointmentRescheduleSerializer,
    AppointmentCancelSerializer,
    AppointmentCompleteSerializer,
)
from .permissions import (
    IsAuthenticatedAndActive,
    CanViewAppointment,
    CanCreateAppointment,
    CanUpdateAppointment,
)


_AppointmentEnvelope = success_envelope("AppointmentEnvelope", AppointmentSerializer())


# ============================================================
# Appointment List & Create
# ============================================================
class AppointmentListCreateView(generics.ListCreateAPIView):
    """
    List & Create Appointments.

    READ:
    - Patient        → sees only his own appointments (read-only)
    - Student        → sees appointments for his assigned cases
    - Supervisor     → sees appointments under his supervision
    - UniversityAdmin→ sees appointments within his university (read-only)
    - TechSupport    → sees all appointments (system-wide archive)

    CREATE:
    - Student        → primary creator (normal workflow)
    - Supervisor     → exceptional creator (academic oversight)

    Notes:
    - Patient CANNOT create appointments
    - All permission validation is enforced in:
        - permissions.py
        - serializers.py
    """

    permission_classes = [IsAuthenticatedAndActive]

    def get_queryset(self):
        """
        Return appointments scoped by user role.

        This ensures:
        - No cross-university leakage
        - No cross-patient leakage
        - Full audit visibility for IT Support
        """
        user = self.request.user
        role = user.role.name

        base_qs = Appointment.objects.select_related(
            "case",
            "patient",
            "student",
            "supervisor",
            "case__university",
        )

        if role == Role.TECH_SUPPORT:
            # System-wide archive access
            return base_qs

        if role == Role.PATIENT:
            # Patient sees only his appointments
            return base_qs.filter(patient=user)

        if role == Role.STUDENT:
            # Student sees appointments he manages
            return base_qs.filter(student=user)

        if role == Role.SUPERVISOR:
            # Supervisor sees appointments under supervision
            return base_qs.filter(supervisor=user)

        if role == Role.UNIVERSITY_ADMIN:
            # University admin sees appointments within his university
            university = user.universityadminprofile_profile.university
            return base_qs.filter(case__university=university)

        # Fallback: no access
        return Appointment.objects.none()

    def get_serializer_class(self):
        """
        Dynamically select serializer.

        - POST  → creation rules
        - GET   → read-only representation
        """
        if self.request.method == "POST":
            return AppointmentCreateSerializer
        return AppointmentSerializer

    def perform_create(self, serializer):
        serializer.save()

    def get_permissions(self):
        base = [IsAuthenticatedAndActive()]
        if self.request.method == "POST":
            base.append(CanCreateAppointment())
        return base


# ============================================================
# Appointment Detail & Update
# ============================================================
class AppointmentDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve & Update Appointment.

    READ:
    - Controlled via CanViewAppointment

    UPDATE:
    - Student    → can update date / notes / limited status
    - Supervisor → can update status only
    - Patient    → NO updates allowed
    - Admin/IT   → NO medical updates allowed

    Final states (completed/cancelled/no-show) are immutable.
    """

    queryset = Appointment.objects.select_related(
        "case",
        "patient",
        "student",
        "supervisor",
        "case__university",
    )

    permission_classes = [
        IsAuthenticatedAndActive,
        CanViewAppointment,
        CanUpdateAppointment,
    ]

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticatedAndActive(), CanViewAppointment()]
        return [
            IsAuthenticatedAndActive(),
            CanViewAppointment(),
            CanUpdateAppointment(),
        ]

    def get_serializer_class(self):
        """
        Use update serializer only for write operations.
        """
        if self.request.method in ("PUT", "PATCH"):
            return AppointmentUpdateSerializer
        return AppointmentSerializer


# ============================================================
# Appointment Actions: Reschedule / Cancel / Complete
# ============================================================

class AppointmentRescheduleView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    @extend_schema(request=AppointmentRescheduleSerializer, responses={200: _AppointmentEnvelope, 400: DetailMessage, 403: DetailMessage, 404: DetailMessage}, tags=["appointments"])
    def post(self, request, pk):
        appointment = Appointment.objects.select_related("case", "patient", "student", "supervisor").filter(id=pk).first()
        if not appointment:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        role = getattr(getattr(user, "role", None), "name", None)
        if role == Role.PATIENT and appointment.patient_id != user.id:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        if role == Role.STUDENT and appointment.student_id != user.id:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        if role == Role.SUPERVISOR and appointment.supervisor_id != user.id:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        if role not in {Role.PATIENT, Role.STUDENT, Role.SUPERVISOR}:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AppointmentRescheduleSerializer(data=request.data, context={"appointment": appointment, "request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        appointment.scheduled_at = data["scheduled_at"]
        appointment.duration_minutes = data["duration_minutes"]
        appointment.location = data.get("location")
        appointment.telehealth_link = data.get("telehealth_link")
        appointment.status = Appointment.Status.RESCHEDULED
        if data.get("reason"):
            appointment.notes = f"{appointment.notes or ''}\n[Reschedule] {data['reason']}".strip()
        appointment.save()

        CaseHistory.objects.create(
            case=appointment.case,
            action=CaseHistory.Action.STATUS_CHANGED,
            description="Appointment rescheduled.",
            performed_by=user,
        )
        return Response({"status": "success", "data": AppointmentSerializer(appointment).data})


class AppointmentCancelView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    @extend_schema(request=AppointmentCancelSerializer, responses={200: _AppointmentEnvelope, 400: DetailMessage, 403: DetailMessage, 404: DetailMessage}, tags=["appointments"])
    def post(self, request, pk):
        appointment = Appointment.objects.select_related("case", "patient", "student", "supervisor").filter(id=pk).first()
        if not appointment:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        role = getattr(getattr(user, "role", None), "name", None)
        if role not in {Role.PATIENT, Role.SUPERVISOR}:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        if role == Role.PATIENT and appointment.patient_id != user.id:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        if role == Role.SUPERVISOR and appointment.supervisor_id != user.id:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AppointmentCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if appointment.status in {Appointment.Status.COMPLETED, Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW}:
            return Response({"detail": "Appointment already finalized."}, status=status.HTTP_400_BAD_REQUEST)

        appointment.status = Appointment.Status.CANCELLED
        reason = serializer.validated_data["reason"]
        appointment.notes = f"{appointment.notes or ''}\n[Cancelled] {reason}".strip()
        appointment.save()

        CaseHistory.objects.create(
            case=appointment.case,
            action=CaseHistory.Action.STATUS_CHANGED,
            description="Appointment cancelled.",
            performed_by=user,
        )
        return Response({"status": "success", "data": AppointmentSerializer(appointment).data})


class AppointmentCompleteView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    @extend_schema(request=AppointmentCompleteSerializer, responses={200: _AppointmentEnvelope, 400: DetailMessage, 403: DetailMessage, 404: DetailMessage}, tags=["appointments"])
    def post(self, request, pk):
        appointment = Appointment.objects.select_related("case", "patient", "student", "supervisor").filter(id=pk).first()
        if not appointment:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        role = getattr(getattr(user, "role", None), "name", None)
        if role not in {Role.STUDENT, Role.SUPERVISOR}:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        if role == Role.STUDENT and appointment.student_id != user.id:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        if role == Role.SUPERVISOR and appointment.supervisor_id != user.id:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AppointmentCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if appointment.status in {Appointment.Status.COMPLETED, Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW}:
            return Response({"detail": "Appointment already finalized."}, status=status.HTTP_400_BAD_REQUEST)

        outcome = serializer.validated_data["outcome"]
        notes = serializer.validated_data.get("notes")
        appointment.status = outcome
        if notes:
            appointment.notes = f"{appointment.notes or ''}\n[Outcome] {notes}".strip()
        appointment.save()

        CaseHistory.objects.create(
            case=appointment.case,
            action=CaseHistory.Action.STATUS_CHANGED,
            description=f"Appointment marked as {outcome}.",
            performed_by=user,
        )
        return Response({"status": "success", "data": AppointmentSerializer(appointment).data})
