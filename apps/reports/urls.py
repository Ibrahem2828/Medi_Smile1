# apps/reports/urls.py
from django.urls import path
from .views import (
    ReportListView,
    ReportDetailView,
    ReportGenerateView,
    ReportSubmitView,
    ReportReviewView,
    StudentReportsView,
    UniversityReportsView,
)

app_name = "reports"

urlpatterns = [
    # Core
    path("", ReportListView.as_view(), name="report-list"),
    path("generate/", ReportGenerateView.as_view(), name="report-generate"),
    path("submit/", ReportSubmitView.as_view(), name="report-submit"),
    path("<uuid:pk>/", ReportDetailView.as_view(), name="report-detail"),
    path("<uuid:pk>/review/", ReportReviewView.as_view(), name="report-review"),

    # Scoped
    path("students/<uuid:student_id>/", StudentReportsView.as_view(), name="student-reports"),
    path("universities/<uuid:university_id>/", UniversityReportsView.as_view(), name="university-reports"),
]
