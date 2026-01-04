# apps/cases/urls.py
from django.urls import path

from .views import (
    CaseListCreateView,
    CaseDetailView,
    CaseStatusUpdateView,
    CaseAssignSupervisorView,
    CaseCreateFromAIView,
    CaseAssignmentRequestCreateView,
    CaseAssignmentRequestDecisionView,
    CaseSessionListView,
    CaseSessionCreateView,
    CaseSessionReviewView,
)

urlpatterns = [
    # =====================================================
    # Cases
    # =====================================================
    path(
        "",
        CaseListCreateView.as_view(),
        name="case-list-create",
    ),
    path(
        "<uuid:pk>/",
        CaseDetailView.as_view(),
        name="case-detail",
    ),
    path(
        "<uuid:pk>/status/",
        CaseStatusUpdateView.as_view(),
        name="case-status-update",
    ),
    path(
        "<uuid:pk>/assign-supervisor/",
        CaseAssignSupervisorView.as_view(),
        name="case-assign-supervisor",
    ),
    path(
        "ai/create/",
        CaseCreateFromAIView.as_view(),
        name="case-create-from-ai",
    ),

    # =====================================================
    # Assignment Requests
    # =====================================================
    path(
        "<uuid:pk>/assignment-requests/",
        CaseAssignmentRequestCreateView.as_view(),
        name="case-assignment-request-create",
    ),
    path(
        "assignment-requests/<uuid:pk>/decision/",
        CaseAssignmentRequestDecisionView.as_view(),
        name="case-assignment-request-decision",
    ),

    # =====================================================
    # Sessions
    # =====================================================
    path(
        "<uuid:case_id>/sessions/",
        CaseSessionListView.as_view(),
        name="case-session-list",
    ),
    path(
        "<uuid:case_id>/sessions/create/",
        CaseSessionCreateView.as_view(),
        name="case-session-create",
    ),
    path(
        "sessions/<uuid:pk>/review/",
        CaseSessionReviewView.as_view(),
        name="case-session-review",
    ),
]
