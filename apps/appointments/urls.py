# apps/appointments/urls.py

from django.urls import path
from . import views

app_name = "appointments"

urlpatterns = [

    # ============================================================
    # Appointments (List / Create)
    # ============================================================
    # GET  : list appointments (role-scoped)
    # POST : create appointment (student / supervisor)
    path(
        "",
        views.AppointmentListView.as_view(),
        name="appointment-list",
    ),

    # ============================================================
    # Appointment Detail (Retrieve / Update)
    # ============================================================
    # GET    : retrieve appointment
    # PATCH  : update appointment (role-based)
    path(
        "<uuid:pk>/",
        views.AppointmentDetailView.as_view(),
        name="appointment-detail",
    ),

    # ============================================================
    # Appointment State Actions
    # ============================================================

    # Patient / Student confirm appointment
    path(
        "<uuid:appointment_id>/actions/confirm/",
        views.confirm_appointment,
        name="appointment-confirm",
    ),

    # Student starts appointment
    path(
        "<uuid:appointment_id>/actions/start/",
        views.start_appointment,
        name="appointment-start",
    ),

    # Student completes appointment
    path(
        "<uuid:appointment_id>/actions/complete/",
        views.complete_appointment,
        name="appointment-complete",
    ),

    # Patient or Student cancels appointment
    path(
        "<uuid:appointment_id>/actions/cancel/",
        views.cancel_appointment,
        name="appointment-cancel",
    ),

    # Student marks appointment as no-show
    path(
        "<uuid:appointment_id>/actions/no-show/",
        views.mark_no_show,
        name="appointment-no-show",
    ),
]
