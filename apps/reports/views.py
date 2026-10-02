# apps/reports/views.py
from django.http import FileResponse, Http404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema

from medismile.utils.auth import resolve_request_user
from apps.accounts.models import User
from apps.universities.models import University

from .models import Report
from .serializers import (
    ReportSerializer,
    ReportCreateSerializer,
    ReportUpdateSerializer,
    ReportSubmitSerializer,
    ReportReviewSerializer,
    ReportRejectSerializer,
    ReportExportSerializer,
)
from .selectors import _resolve_university_id, reports_queryset_for_user, reports_for_student, reports_for_university
from .services import (
    create_report,
    update_report,
    submit_report,
    approve_report,
    reject_report,
    export_report,
    get_export_file_path,
)
from .permissions import (
    CanViewReport,
    CanCreateReport,
    CanApproveReport,
    CanExportReport,
)


class ReportListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), CanCreateReport()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = resolve_request_user(self.request)
        qs = reports_queryset_for_user(user)

        status_filter = self.request.query_params.get("status")
        report_type = self.request.query_params.get("report_type")
        target_type = self.request.query_params.get("target_type")
        target_id = self.request.query_params.get("target_id")

        if status_filter:
            qs = qs.filter(status=status_filter)
        if report_type:
            qs = qs.filter(report_type=report_type)
        if target_type:
            qs = qs.filter(target_type=target_type)
        if target_id:
            qs = qs.filter(target_id=target_id)

        return qs

    def create(self, request, *args, **kwargs):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor = resolve_request_user(request)
        report = create_report(actor=actor, data=serializer.validated_data)
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


class ReportDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, CanViewReport]
    serializer_class = ReportSerializer
    queryset = Report.objects.select_related("author", "student", "supervisor", "university", "approved_by")

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return ReportUpdateSerializer
        return ReportSerializer

    def update(self, request, *args, **kwargs):
        report = self.get_object()
        self.check_object_permissions(request, report)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor = resolve_request_user(request)

        updated = update_report(actor=actor, report=report, data=serializer.validated_data)
        return Response(ReportSerializer(updated).data, status=status.HTTP_200_OK)


class ReportSubmitView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportSubmitSerializer

    def post(self, request, *args, **kwargs):
        report = generics.get_object_or_404(Report, pk=kwargs["pk"])
        actor = resolve_request_user(request)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = submit_report(actor=actor, report=report)
        return Response(ReportSerializer(updated).data, status=status.HTTP_200_OK)


class ReportApproveView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, CanApproveReport]
    serializer_class = ReportReviewSerializer

    def post(self, request, *args, **kwargs):
        report = generics.get_object_or_404(Report, pk=kwargs["pk"])
        actor = resolve_request_user(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = approve_report(
            supervisor=actor,
            report=report,
            review_notes=serializer.validated_data.get("review_notes"),
            score=serializer.validated_data.get("score"),
        )
        return Response(ReportSerializer(updated).data, status=status.HTTP_200_OK)


class ReportRejectView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, CanApproveReport]
    serializer_class = ReportRejectSerializer

    def post(self, request, *args, **kwargs):
        report = generics.get_object_or_404(Report, pk=kwargs["pk"])
        actor = resolve_request_user(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = reject_report(
            supervisor=actor,
            report=report,
            review_notes=serializer.validated_data["review_notes"],
        )
        return Response(ReportSerializer(updated).data, status=status.HTTP_200_OK)


class ReportExportView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, CanExportReport]
    serializer_class = ReportExportSerializer

    def post(self, request, *args, **kwargs):
        report = generics.get_object_or_404(Report, pk=kwargs["pk"])
        actor = resolve_request_user(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_url = export_report(actor=actor, report=report, fmt=serializer.validated_data["format"])
        return Response({"status": "success", "data": {"file_url": file_url}}, status=status.HTTP_200_OK)


class ReportExportFileView(generics.RetrieveAPIView):
    """Download a generated report through an authenticated, scoped route."""

    permission_classes = [IsAuthenticated, CanExportReport]
    queryset = Report.objects.select_related("university")

    @extend_schema(responses={200: OpenApiTypes.BINARY}, tags=["reports"])
    def get(self, request, *args, **kwargs):
        report = self.get_object()
        actor = resolve_request_user(request)
        actor_university_id = _resolve_university_id(actor)
        if not actor_university_id or report.university_id != actor_university_id:
            raise Http404
        export_path = get_export_file_path(report)
        if not export_path:
            raise Http404
        content_type = "application/pdf" if export_path.suffix == ".pdf" else "text/csv; charset=utf-8"
        response = FileResponse(export_path.open("rb"), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="report_{report.id}{export_path.suffix}"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class StudentReportsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)
        student_id = self.kwargs["student_id"]
        student = generics.get_object_or_404(User, id=student_id)
        return reports_for_student(student=student, viewer=user)


class UniversityReportsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReportSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)
        university_id = self.kwargs["university_id"]
        university = generics.get_object_or_404(University, id=university_id)
        return reports_for_university(university=university, viewer=user)
