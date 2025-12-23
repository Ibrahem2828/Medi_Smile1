from __future__ import annotations

from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Report
from .serializers import (
    ReportSerializer,
    ReportCreateSerializer,
    ReportVisibilityUpdateSerializer,
)

from apps.accounts.models import User
from apps.universities.models import University
from apps.accounts.permissions import IsUniversityAdmin, IsTechSupport
from medismile.utils.auth import resolve_request_user, require_request_user


# ============================================================
# Helpers
# ============================================================

def _reports_queryset_for_user(user):
    """
    Centralized scoping for reports visibility.
    """

    base_qs = (
        Report.objects
        .select_related("student", "university", "generated_by")
        .order_by("-generated_at")
    )

    if not user:
        return Report.objects.none()

    # Student → own reports only
    if user.role == "student":
        return base_qs.filter(student=user, is_active=True)

    # Supervisor → reports of students in same university
    if user.role == "supervisor":
        if hasattr(user, "supervisorprofile") and user.supervisorprofile.university:
            return base_qs.filter(
                university=user.supervisorprofile.university,
                is_active=True,
            )
        return Report.objects.none()

    # Admin / Tech → full access
    if user.role in ["university_admin", "tech_support"]:
        return base_qs

    return Report.objects.none()


# ============================================================
# Report List & Generate
# ============================================================

class ReportListView(generics.ListCreateAPIView):
    """
    List & Generate reports.

    GET:
    - Student: own reports
    - Supervisor: reports of same university
    - Admin / Tech: all

    POST:
    - Generate new report (restricted)
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = resolve_request_user(self.request)
        qs = _reports_queryset_for_user(user)

        # Optional filters
        student_id = self.request.query_params.get("student_id")
        university_id = self.request.query_params.get("university_id")
        report_type = self.request.query_params.get("report_type")
        is_active = self.request.query_params.get("is_active")

        if student_id:
            qs = qs.filter(student_id=student_id)

        if university_id:
            qs = qs.filter(university_id=university_id)

        if report_type:
            qs = qs.filter(report_type=report_type)

        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        return qs

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ReportCreateSerializer
        return ReportSerializer

    def perform_create(self, serializer):
        """
        Generation handled entirely inside serializer.
        """
        serializer.save()


# ============================================================
# Report Detail (Read + Soft Visibility Update)
# ============================================================

class ReportDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve report details.

    PATCH:
    - Only admins can toggle is_active
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = resolve_request_user(self.request)
        return _reports_queryset_for_user(user)

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ReportVisibilityUpdateSerializer
        return ReportSerializer


# ============================================================
# Student Reports (Explicit Endpoint)
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_reports(request, student_id):
    """
    Get reports for a specific student.

    - Student: self only
    - Supervisor/Admin: allowed
    """

    user, error = require_request_user(request)
    if error:
        return error

    try:
        student = User.objects.get(id=student_id, role="student")
    except User.DoesNotExist:
        return Response(
            {"error": _("Student not found")},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Authorization
    if user.role == "student" and user != student:
        return Response(
            {"error": _("You are not authorized to view these reports")},
            status=status.HTTP_403_FORBIDDEN,
        )

    if user.role == "supervisor":
        if not hasattr(user, "supervisorprofile") or (
            user.supervisorprofile.university != student.studentprofile.university
        ):
            return Response(
                {"error": _("Access denied")},
                status=status.HTTP_403_FORBIDDEN,
            )

    reports = (
        Report.objects
        .filter(student=student, is_active=True)
        .select_related("student", "university", "generated_by")
    )

    serializer = ReportSerializer(reports, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ============================================================
# University Reports
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsUniversityAdmin | IsTechSupport])
def university_reports(request, university_id):
    """
    Get all reports for a university.
    """

    user, error = require_request_user(request)
    if error:
        return error

    try:
        university = University.objects.get(id=university_id)
    except University.DoesNotExist:
        return Response(
            {"error": _("University not found")},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Supervisor restriction
    if user.role == "supervisor":
        if not hasattr(user, "supervisorprofile") or (
            user.supervisorprofile.university != university
        ):
            return Response(
                {"error": _("Access denied")},
                status=status.HTTP_403_FORBIDDEN,
            )

    reports = (
        Report.objects
        .filter(university=university, is_active=True)
        .select_related("student", "generated_by")
    )

    serializer = ReportSerializer(reports, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)
