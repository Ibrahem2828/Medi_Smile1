from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [

    # ============================================================
    # Reports (Core)
    # ============================================================
    # List all reports / Generate new report
    path(
        "",
        views.ReportListView.as_view(),
        name="report-list",
    ),

    # Retrieve single report / Update visibility
    path(
        "<uuid:pk>/",
        views.ReportDetailView.as_view(),
        name="report-detail",
    ),

    # ============================================================
    # Scoped Reports
    # ============================================================
    # Reports for a specific student
    path(
        "students/<uuid:student_id>/",
        views.student_reports,
        name="student-reports",
    ),

    # Reports for a specific university
    path(
        "universities/<uuid:university_id>/",
        views.university_reports,
        name="university-reports",
    ),

]
