# apps/ai/selectors.py
from django.db.models import QuerySet
from apps.accounts.models import Role
from apps.cases.models import Case
from medismile.utils.scoping import get_user_university_id
from .models import AIDiagnosis


def get_ai_diagnosis_queryset_for_user(*, user) -> QuerySet[AIDiagnosis]:
    qs = AIDiagnosis.objects.select_related("case", "patient", "requested_by", "reviewed_by")

    role = getattr(getattr(user, "role", None), "name", None)

    if role == Role.TECH_SUPPORT:
        # Operational support does not imply blanket access to clinical AI
        # output. Health/config has its own minimal permission endpoint.
        return qs.none()

    if role == Role.PATIENT:
        return qs.filter(patient=user)

    if role == Role.STUDENT:
        case_ids = Case.objects.filter(student=user).values_list("id", flat=True)
        return qs.filter(case_id__in=case_ids)

    if role == Role.SUPERVISOR:
        case_ids = Case.objects.filter(supervisor=user).values_list("id", flat=True)
        return qs.filter(case_id__in=case_ids)

    if role == Role.UNIVERSITY_ADMIN:
        # Admin sees diagnoses for cases in their university only. Without a
        # resolved university they see nothing (never the unscoped cases).
        university_id = get_user_university_id(user)
        if not university_id:
            return qs.none()
        return qs.filter(case__university_id=university_id)

    return qs.none()
