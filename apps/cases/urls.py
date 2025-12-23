from django.urls import path
from . import views

app_name = "cases"

urlpatterns = [

    # ============================================================
    # Cases
    # ============================================================

    # List cases (role-based) / Create case
    path(
        "",
        views.CaseListView.as_view(),
        name="case-list",
    ),

    # Retrieve / Update single case
    path(
        "<uuid:pk>/",
        views.CaseDetailView.as_view(),
        name="case-detail",
    ),

    # ============================================================
    # Assignment Requests (Case → Student → Supervisor)
    # ============================================================

    # List assignment requests:
    # - student: own requests
    # - supervisor: requests for supervised cases
    # - admin / IT: all
    #
    # Create request (student only)
    path(
        "assignment-requests/",
        views.CaseAssignmentRequestListView.as_view(),
        name="assignment-request-list",
    ),

    # Supervisor:
    # Retrieve / Accept / Reject assignment request
    path(
        "assignment-requests/<uuid:pk>/",
        views.CaseAssignmentRequestDetailView.as_view(),
        name="assignment-request-detail",
    ),

    # ============================================================
    # Treatment Sessions (per Case)
    # ============================================================

    # List sessions for a case / Create session (student)
    path(
        "<uuid:case_id>/sessions/",
        views.CaseSessionListCreateView.as_view(),
        name="case-session-list-create",
    ),

    # Supervisor reviews a session
    path(
        "sessions/<uuid:pk>/review/",
        views.CaseSessionReviewView.as_view(),
        name="case-session-review",
    ),

    # ============================================================
    # Legacy APIs (Backward Compatibility)
    # ============================================================

    # Student requests assignment (legacy endpoint)
    path(
        "<uuid:case_id>/assignments/request/",
        views.request_case_assignment,
        name="case-request-assignment-legacy",
    ),
]
