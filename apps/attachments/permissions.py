# apps/attachments/permissions.py
from rest_framework.permissions import BasePermission

from apps.accounts.models import Role
from .models import Attachment


# ============================================================
# Helpers
# ============================================================
def is_student_owner(user, attachment: Attachment) -> bool:
    return attachment.uploaded_by_id == user.id


def is_patient_owner(user, attachment: Attachment) -> bool:
    return attachment.case.patient_id == user.id


def is_supervisor(user, attachment: Attachment) -> bool:
    return attachment.case.supervisor_id == user.id


def is_university_admin(user, attachment: Attachment) -> bool:
    try:
        profile = user.universityadminprofile_profile
    except Exception:
        return False
    return attachment.case.university_id == profile.university_id


# ============================================================
# Base
# ============================================================
class IsAuthenticatedAndActive(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )


# ============================================================
# View Permission
# ============================================================
class CanViewAttachment(BasePermission):
    """
    READ permissions:
    - Student        → attachments of his appointments
    - Supervisor     → attachments of supervised cases
    - Patient        → only visible attachments of his case
    - UniversityAdmin→ read-only within university
    - TechSupport    → full read
    """

    def has_object_permission(self, request, view, obj: Attachment):
        user = request.user
        role = user.role.name

        if role == Role.TECH_SUPPORT:
            return True

        if role == Role.STUDENT:
            return is_student_owner(user, obj)

        if role == Role.SUPERVISOR:
            return is_supervisor(user, obj)

        if role == Role.PATIENT:
            return is_patient_owner(user, obj) and obj.is_visible_to_patient

        if role == Role.UNIVERSITY_ADMIN:
            return is_university_admin(user, obj)

        return False


# ============================================================
# Create Permission
# ============================================================
class CanCreateAttachment(BasePermission):
    """
    CREATE permissions:
    - Student only
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role.name == Role.STUDENT
        )


# ============================================================
# Delete Permission (Soft rules)
# ============================================================
class CanDeleteAttachment(BasePermission):
    """
    DELETE permissions:
    - Student: only his own attachment
    - Supervisor / Admin / IT: ❌ (medical integrity)
    """

    def has_object_permission(self, request, view, obj: Attachment):
        return (
            request.user.role.name == Role.STUDENT
            and is_student_owner(request.user, obj)
        )
