# apps/cases/urls.py
from django.urls import path

from .views import (
    CaseListCreateView,
    CaseDetailView,
    CaseAssignmentRequestCreateView,
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

    # =====================================================
    # Assignment Requests
    # =====================================================
    path(
        "<uuid:pk>/assignment-requests/",
        CaseAssignmentRequestCreateView.as_view(),
        name="case-assignment-request-create",
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
