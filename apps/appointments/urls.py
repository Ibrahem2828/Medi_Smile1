# apps/appointments/urls.py
from django.urls import path

from .views import (
    AppointmentListCreateView,
    AppointmentDetailView,
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
]
