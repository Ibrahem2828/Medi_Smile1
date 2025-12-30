# apps/reports/views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from medismile.utils.auth import resolve_request_user
from apps.accounts.models import Role

from .models import Report
from .serializers import (
    ReportSerializer,
    ReportSubmitSerializer,
    ReportGenerateSerializer,
    ReportReviewSerializer,
    ReportVisibilityUpdateSerializer,
)
from .selectors import (
    reports_queryset_for_user,
    reports_for_student,
    reports_for_university,
)
from .services import generate_report, toggle_report_visibility, submit_report, review_report
from .permissions import (
    CanViewReport,
    CanGenerateReport,
    CanToggleReportVisibility,
)


# ============================================================
# Reports List & Generate
# ============================================================

class ReportListView(generics.ListAPIView):
    """
    GET: Scoped list of reports (student / supervisor / admin / tech)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ReportSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)
        qs = reports_queryset_for_user(user)

        # Optional filters
        student_id = self.request.query_params.get("student_id")
        university_id = self.request.query_params.get("university_id")
        report_type = self.request.query_params.get("report_type")

        if student_id:
            qs = qs.filter(student_id=student_id)
        if university_id:
            qs = qs.filter(university_id=university_id)
        if report_type:
            qs = qs.filter(report_type=report_type)

        return qs


# ============================================================
# Report Detail (Read + Visibility Toggle)
# ============================================================

class ReportDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, CanViewReport]
    serializer_class = ReportSerializer
    queryset = Report.objects.select_related("student", "university", "generated_by")

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ReportVisibilityUpdateSerializer
        return ReportSerializer

    def update(self, request, *args, **kwargs):
        report = self.get_object()
        self.check_object_permissions(request, report)

        self.permission_classes = [IsAuthenticated, CanToggleReportVisibility]

        serializer = self.get_serializer(report, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        actor = resolve_request_user(request)
        report = toggle_report_visibility(
            actor=actor,
            report=report,
            is_active=serializer.validated_data["is_active"],
        )

        return Response(
            ReportSerializer(report).data,
            status=status.HTTP_200_OK,
        )


# ============================================================
# Generate Report (Supervisor/Admin/Tech)
# ============================================================

class ReportGenerateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, CanGenerateReport]
    serializer_class = ReportGenerateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor = resolve_request_user(request)
        report = generate_report(actor=actor, data=serializer.validated_data)
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


# ============================================================
# Submit Report (Student)
# ============================================================

class ReportSubmitView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportSubmitSerializer

    def create(self, request, *args, **kwargs):
        actor = resolve_request_user(request)
        if getattr(getattr(actor, "role", None), "name", None) != Role.STUDENT:
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data, context={"student": actor})
        serializer.is_valid(raise_exception=True)
        report = submit_report(student=actor, data=serializer.validated_data)
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


# ============================================================
# Review Report (Supervisor)
# ============================================================

class ReportReviewView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportReviewSerializer

    def post(self, request, *args, **kwargs):
        report = generics.get_object_or_404(Report, pk=kwargs["pk"])
        actor = resolve_request_user(request)
        if getattr(getattr(actor, "role", None), "name", None) != Role.SUPERVISOR:
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = review_report(
            supervisor=actor,
            report=report,
            feedback=serializer.validated_data["feedback"],
            score=serializer.validated_data.get("score"),
        )
        return Response(ReportSerializer(updated).data, status=status.HTTP_200_OK)


# ============================================================
# Student Reports
# ============================================================

class StudentReportsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)
        student_id = self.kwargs["student_id"]
        return reports_for_student(student=user.__class__.objects.get(id=student_id), viewer=user)


# ============================================================
# University Reports
# ============================================================

class UniversityReportsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)
        university_id = self.kwargs["university_id"]
        return reports_for_university(
            university=user.university.__class__.objects.get(id=university_id),
            viewer=user,
        )
