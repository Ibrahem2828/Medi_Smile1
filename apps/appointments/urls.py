# apps/appointments/urls.py
from django.urls import path

from .views import (
    AppointmentListCreateView,
    AppointmentDetailView,
    AppointmentRescheduleView,
    AppointmentCancelView,
    AppointmentCompleteView,
)

urlpatterns = [
    # =====================================================
    # Appointments
    # =====================================================
    path(
        "",
        AppointmentListCreateView.as_view(),
        name="appointment-list-create",
    ),
    path(
        "<uuid:pk>/",
        AppointmentDetailView.as_view(),
        name="appointment-detail",
    ),
    path(
        "<uuid:pk>/reschedule/",
        AppointmentRescheduleView.as_view(),
        name="appointment-reschedule",
    ),
    path(
        "<uuid:pk>/cancel/",
        AppointmentCancelView.as_view(),
        name="appointment-cancel",
    ),
    path(
        "<uuid:pk>/complete/",
        AppointmentCompleteView.as_view(),
        name="appointment-complete",
    ),
]
