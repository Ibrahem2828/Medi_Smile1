# apps/reports/urls.py
from django.urls import path
from .views import (
    ReportListView,
    ReportDetailView,
    StudentReportsView,
    UniversityReportsView,
)

app_name = "reports"

urlpatterns = [
    # Core
    path("", ReportListView.as_view(), name="report-list"),
    path("<uuid:pk>/", ReportDetailView.as_view(), name="report-detail"),

    # Scoped
    path("students/<uuid:student_id>/", StudentReportsView.as_view(), name="student-reports"),
    path("universities/<uuid:university_id>/", UniversityReportsView.as_view(), name="university-reports"),
]
