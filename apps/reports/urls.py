# apps/reports/urls.py
from django.urls import path
from .views import (
    ReportListCreateView,
    ReportDetailView,
    ReportSubmitView,
    ReportApproveView,
    ReportRejectView,
    ReportExportView,
    StudentReportsView,
    UniversityReportsView,
)

app_name = "reports"

urlpatterns = [
    # Core
    path("", ReportListCreateView.as_view(), name="report-list"),
    path("<uuid:pk>/", ReportDetailView.as_view(), name="report-detail"),
    path("<uuid:pk>/submit/", ReportSubmitView.as_view(), name="report-submit"),
    path("<uuid:pk>/approve/", ReportApproveView.as_view(), name="report-approve"),
    path("<uuid:pk>/reject/", ReportRejectView.as_view(), name="report-reject"),
    path("<uuid:pk>/export/", ReportExportView.as_view(), name="report-export"),

    # Scoped
    path("students/<uuid:student_id>/", StudentReportsView.as_view(), name="student-reports"),
    path("universities/<uuid:university_id>/", UniversityReportsView.as_view(), name="university-reports"),
]
