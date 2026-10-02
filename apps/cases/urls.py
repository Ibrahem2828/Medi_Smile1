# apps/cases/urls.py
from django.urls import path

from .views import (
    CaseListCreateView,
    CaseDetailView,
    CaseStatusUpdateView,
    CaseAssignSupervisorView,
    CaseAssignmentRequestCreateView,
    CaseAssignmentRequestDecisionView,
    CaseSessionListView,
    CaseSessionCreateView,
    CaseSessionReviewView,
    AICriticalCaseCreateView,
    AIProposalIngestView,
    AIProposalNextView,
    AIProposalDecisionView,
    SupervisorNewCasesView,
    SupervisorCaseDecisionView,
    StudentAvailableCasesView,
    StudentRequestAssignmentView,
    SupervisorAssignmentRequestsView,
    SupervisorAssignmentDecisionView,
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

    # =====================================================
    # AI Proposals (patient review)
    # =====================================================
    path(
        "ai/create/",
        AICriticalCaseCreateView.as_view(),
        name="ai-critical-case-create",
    ),
    path(
        "ai/proposals/",
        AIProposalIngestView.as_view(),
        name="ai-proposal-ingest",
    ),
    path(
        "ai/proposals/<uuid:session_id>/next/",
        AIProposalNextView.as_view(),
        name="ai-proposal-next",
    ),
    path(
        "ai/proposals/<uuid:session_id>/decision/",
        AIProposalDecisionView.as_view(),
        name="ai-proposal-decision",
    ),

    # =====================================================
    # Supervisor: new cases decision
    # =====================================================
    path(
        "supervisor/new/",
        SupervisorNewCasesView.as_view(),
        name="supervisor-new-cases",
    ),
    path(
        "<uuid:case_id>/supervisor-decision/",
        SupervisorCaseDecisionView.as_view(),
        name="supervisor-case-decision",
    ),

    # =====================================================
    # Student: available cases & assignment
    # =====================================================
    path(
        "student/available/",
        StudentAvailableCasesView.as_view(),
        name="student-available-cases",
    ),
    path(
        "<uuid:case_id>/request-assignment/",
        StudentRequestAssignmentView.as_view(),
        name="student-request-assignment",
    ),

    # =====================================================
    # Supervisor: assignment decisions
    # =====================================================
    path(
        "supervisor/assignment-requests/",
        SupervisorAssignmentRequestsView.as_view(),
        name="supervisor-assignment-requests",
    ),
    path(
        "<uuid:case_id>/assignment-decision/",
        SupervisorAssignmentDecisionView.as_view(),
        name="supervisor-assignment-decision",
    ),
]
