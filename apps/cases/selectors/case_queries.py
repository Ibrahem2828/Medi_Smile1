# apps/cases/selectors/case_queries.py

from typing import Optional
from django.db.models import QuerySet, Q

from apps.accounts.models import User, Role
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
    role_name = getattr(getattr(user, "role", None), "name", None)

    if role_name == Role.PATIENT:
        return Case.objects.filter(patient=user)

    if role_name == Role.STUDENT:
        student_university_id = getattr(getattr(user, "studentprofile_profile", None), "university_id", None)
        return Case.objects.filter(
            Q(student=user) | Q(is_public=True, university_id=student_university_id)
        )

    if role_name == Role.SUPERVISOR:
        return Case.objects.filter(supervisor=user)

    if role_name in {Role.UNIVERSITY_ADMIN, Role.TECH_SUPPORT}:
        return Case.objects.all()

    return Case.objects.none()


def get_active_case_for_patient(patient: User) -> Optional[Case]:
    """
    Return the active case for a patient (if any).
    """

    if getattr(getattr(patient, "role", None), "name", None) != Role.PATIENT:
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


def get_public_cases(*, university_id: Optional[str] = None) -> QuerySet[Case]:
    """
    Return cases open for student assignment.
    """

    qs = Case.objects.filter(
        is_public=True,
        status=Case.Status.ACCEPTED,
    )

    if university_id:
        qs = qs.filter(university_id=university_id)

    return qs


# ============================================================
# Assignment Requests Queries
# ============================================================

def get_assignment_requests_for_user(user: User) -> QuerySet[CaseAssignmentRequest]:
    """
    Return assignment requests visible to user.
    """
    role_name = getattr(getattr(user, "role", None), "name", None)

    if role_name == Role.STUDENT:
        return CaseAssignmentRequest.objects.filter(student=user)

    if role_name == Role.SUPERVISOR:
        return CaseAssignmentRequest.objects.filter(case__supervisor=user)

    if role_name in {Role.UNIVERSITY_ADMIN, Role.TECH_SUPPORT}:
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

    role_name = getattr(getattr(user, "role", None), "name", None)

    if role_name == Role.STUDENT:
        return qs.filter(student=user)

    if role_name == Role.SUPERVISOR:
        return qs.filter(supervisor=user)

    if role_name == Role.PATIENT:
        return qs.filter(case__patient=user)

    if role_name in {Role.UNIVERSITY_ADMIN, Role.TECH_SUPPORT}:
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
