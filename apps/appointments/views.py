# apps/appointments/views.py
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Role

from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    AppointmentCreateSerializer,
    AppointmentUpdateSerializer,
)
from .permissions import (
    IsAuthenticatedAndActive,
    CanViewAppointment,
    CanCreateAppointment,
    CanUpdateAppointment,
)


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
        """
        Create appointment.

        Business rules enforced in:
        - AppointmentCreateSerializer.validate()
        - Appointment.clean()

        Future hooks:
        - Notification scheduling (patient / student / supervisor)
        - Audit logging
        """
        serializer.save(context={"request": self.request})


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

    def get_serializer_class(self):
        """
        Use update serializer only for write operations.
        """
        if self.request.method in ("PUT", "PATCH"):
            return AppointmentUpdateSerializer
        return AppointmentSerializer
