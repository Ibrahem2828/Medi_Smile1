# apps/appointments/views.py
from __future__ import annotations

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from medismile.utils.auth import resolve_request_user, require_request_user
from medismile.utils.pagination import StandardResultsSetPagination

from apps.accounts.permissions import IsStudent
from apps.notifications.utils import notify_appointment_status_change

from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    AppointmentCreateSerializer,
    AppointmentUpdateSerializer,
)


# ============================================================
# Unified API Helpers
# ============================================================

def api_success(message, data=None, status_code=status.HTTP_200_OK):
    return Response(
        {
            "status": "success",
            "message": message,
            "data": data,
        },
        status=status_code,
    )


def api_error(message, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {
            "status": "error",
            "message": message,
        },
        status=status_code,
    )


# ============================================================
# Appointment List & Create
# ============================================================

class AppointmentListView(generics.ListCreateAPIView):
    """
    List & create appointments.

    Visibility rules:
    - Patient: own appointments only
    - Student: appointments of cases assigned to him
    - Supervisor: appointments of supervised cases
    - University admin / IT support: full access
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = resolve_request_user(self.request)

        qs = (
            Appointment.objects
            .select_related("patient", "student", "supervisor", "case", "created_by")
            .filter(is_archived=False)
        )

        if not user:
            return Appointment.objects.none()

        if user.role == "patient":
            qs = qs.filter(patient=user)

        elif user.role == "student":
            qs = qs.filter(student=user)

        elif user.role == "supervisor":
            qs = qs.filter(supervisor=user)

        elif user.role in ["university_admin", "tech_support"]:
            pass  # full access

        else:
            return Appointment.objects.none()

        # Optional filters
        status_filter = self.request.query_params.get("status")
        case_id = self.request.query_params.get("case_id")

        if status_filter:
            qs = qs.filter(status=status_filter)

        if case_id:
            qs = qs.filter(case_id=case_id)

        return qs.order_by("-appointment_date")

    def get_serializer_class(self):
        return (
            AppointmentCreateSerializer
            if self.request.method == "POST"
            else AppointmentSerializer
        )

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save()


# ============================================================
# Appointment Detail & Update
# ============================================================

class AppointmentDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update an appointment.
    Deletion is NOT allowed (medical/legal reasons).
    """

    queryset = (
        Appointment.objects
        .select_related("patient", "student", "supervisor", "case", "created_by")
        .all()
    )
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return (
            AppointmentUpdateSerializer
            if self.request.method in ["PUT", "PATCH"]
            else AppointmentSerializer
        )

    def get_object(self):
        appointment = super().get_object()
        user = resolve_request_user(self.request)

        if not user:
            return appointment

        if user.role == "patient" and appointment.patient != user:
            raise PermissionError(_("Access denied."))

        if user.role == "student" and appointment.student != user:
            raise PermissionError(_("Access denied."))

        if user.role == "supervisor" and appointment.supervisor != user:
            raise PermissionError(_("Access denied."))

        return appointment


# ============================================================
# Appointment State Actions
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def confirm_appointment(request, appointment_id):
    """
    Confirm appointment:
    - Patient confirms attendance
    - Student confirms scheduling
    """

    appointment = get_object_or_404(Appointment, id=appointment_id)
    user, error = require_request_user(request)
    if error:
        return error

    if appointment.status != Appointment.Status.SCHEDULED:
        return api_error(_("Appointment cannot be confirmed."))

    if user not in {appointment.patient, appointment.student}:
        return api_error(_("Not authorized."), status.HTTP_403_FORBIDDEN)

    old_status = appointment.status
    appointment.status = Appointment.Status.CONFIRMED
    appointment.save(update_fields=["status"])

    notify_appointment_status_change(
        appointment, old_status, appointment.status, user
    )

    return api_success(
        _("Appointment confirmed successfully."),
        AppointmentSerializer(appointment).data,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
@transaction.atomic
def start_appointment(request, appointment_id):
    """
    Start appointment (student only).
    """

    appointment = get_object_or_404(Appointment, id=appointment_id)
    user, error = require_request_user(request)
    if error:
        return error

    if appointment.student != user:
        return api_error(_("Not authorized."), status.HTTP_403_FORBIDDEN)

    if appointment.status != Appointment.Status.CONFIRMED:
        return api_error(_("Appointment must be confirmed first."))

    appointment.status = Appointment.Status.IN_PROGRESS
    appointment.save(update_fields=["status"])

    return api_success(
        _("Appointment started."),
        AppointmentSerializer(appointment).data,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
@transaction.atomic
def complete_appointment(request, appointment_id):
    """
    Complete appointment (student only).
    """

    appointment = get_object_or_404(Appointment, id=appointment_id)
    user, error = require_request_user(request)
    if error:
        return error

    if appointment.student != user:
        return api_error(_("Not authorized."), status.HTTP_403_FORBIDDEN)

    if appointment.status not in {
        Appointment.Status.CONFIRMED,
        Appointment.Status.IN_PROGRESS,
    }:
        return api_error(_("Appointment cannot be completed."))

    old_status = appointment.status
    appointment.status = Appointment.Status.COMPLETED
    appointment.save(update_fields=["status"])

    notify_appointment_status_change(
        appointment, old_status, appointment.status, user
    )

    return api_success(
        _("Appointment completed."),
        AppointmentSerializer(appointment).data,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cancel_appointment(request, appointment_id):
    """
    Cancel appointment:
    - Patient (own)
    - Student (own)
    """

    appointment = get_object_or_404(Appointment, id=appointment_id)
    user, error = require_request_user(request)
    if error:
        return error

    if user not in {appointment.patient, appointment.student}:
        return api_error(_("Not authorized."), status.HTTP_403_FORBIDDEN)

    if appointment.status not in {
        Appointment.Status.SCHEDULED,
        Appointment.Status.CONFIRMED,
    }:
        return api_error(_("Appointment cannot be cancelled."))

    old_status = appointment.status
    appointment.status = Appointment.Status.CANCELLED
    appointment.save(update_fields=["status"])

    notify_appointment_status_change(
        appointment, old_status, appointment.status, user
    )

    return api_success(
        _("Appointment cancelled."),
        AppointmentSerializer(appointment).data,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
@transaction.atomic
def mark_no_show(request, appointment_id):
    """
    Mark appointment as no-show (student only).
    """

    appointment = get_object_or_404(Appointment, id=appointment_id)
    user, error = require_request_user(request)
    if error:
        return error

    if appointment.student != user:
        return api_error(_("Not authorized."), status.HTTP_403_FORBIDDEN)

    if appointment.status not in {
        Appointment.Status.CONFIRMED,
        Appointment.Status.IN_PROGRESS,
    }:
        return api_error(_("Invalid appointment status."))

    appointment.status = Appointment.Status.NO_SHOW
    appointment.save(update_fields=["status"])

    return api_success(
        _("Appointment marked as no-show."),
        AppointmentSerializer(appointment).data,
    )
