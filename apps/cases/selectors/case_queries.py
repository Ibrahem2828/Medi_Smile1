# apps/cases/selectors/case_queries.py

from typing import Optional
from django.db.models import QuerySet, Q

from apps.accounts.models import User
from apps.cases.models import (
    Case,
    CaseAssignmentRequest,
    CaseSession,
)


# ============================================================
# Case Queries
# ============================================================

def get_cases_for_user(user: User) -> QuerySet[Case]:
    """
    Return cases visible to a user based on their role.
    """

    if user.role == "patient":
        return Case.objects.filter(patient=user)

    if user.role == "student":
        return Case.objects.filter(
            Q(student=user) | Q(is_public=True)
        )

    if user.role == "supervisor":
        return Case.objects.filter(supervisor=user)

    if user.role in {"university_admin", "tech_support"}:
        return Case.objects.all()

    return Case.objects.none()


def get_active_case_for_patient(patient: User) -> Optional[Case]:
    """
    Return the active case for a patient (if any).
    """

    if patient.role != "patient":
        return None

    return (
        Case.objects
        .filter(
            patient=patient,
            status__in=Case.ACTIVE_STATUSES,
        )
        .order_by("-created_at")
        .first()
    )


def get_public_cases() -> QuerySet[Case]:
    """
    Return cases open for student assignment.
    """

    return Case.objects.filter(
        is_public=True,
        status=Case.Status.PENDING_ASSIGNMENT,
    )


# ============================================================
# Assignment Requests Queries
# ============================================================

def get_assignment_requests_for_user(user: User) -> QuerySet[CaseAssignmentRequest]:
    """
    Return assignment requests visible to user.
    """

    if user.role == "student":
        return CaseAssignmentRequest.objects.filter(student=user)

    if user.role == "supervisor":
        return CaseAssignmentRequest.objects.filter(case__supervisor=user)

    if user.role in {"university_admin", "tech_support"}:
        return CaseAssignmentRequest.objects.all()

    return CaseAssignmentRequest.objects.none()


def get_assignment_requests_for_case(case: Case) -> QuerySet[CaseAssignmentRequest]:
    """
    Return all assignment requests for a specific case.
    """

    return CaseAssignmentRequest.objects.filter(case=case)


# ============================================================
# Case Sessions Queries
# ============================================================

def get_sessions_for_case(case: Case, *, user: User) -> QuerySet[CaseSession]:
    """
    Return sessions of a case visible to the given user.
    """

    qs = CaseSession.objects.filter(case=case)

    if user.role == "student":
        return qs.filter(student=user)

    if user.role == "supervisor":
        return qs.filter(supervisor=user)

    if user.role == "patient":
        return qs.filter(case__patient=user)

    if user.role in {"university_admin", "tech_support"}:
        return qs

    return CaseSession.objects.none()


# ============================================================
# Utility Queries
# ============================================================

def patient_has_active_case(patient: User) -> bool:
    """
    Check if a patient already has an active case.
    """

    if patient.role != "patient":
        return False

    return Case.objects.filter(
        patient=patient,
        status__in=Case.ACTIVE_STATUSES,
    ).exists()
