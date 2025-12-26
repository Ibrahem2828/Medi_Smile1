# apps/support/selectors.py
from django.db.models import Count, Q
from apps.accounts.models import Role
from .models import SupportTicket, SupportTicketResponse


def get_user_university_ids(user) -> set:
    """
    Collect all university IDs linked to the user.
    Supports FK or M2M.
    """
    ids = set()

    if hasattr(user, "university_id") and user.university_id:
        ids.add(user.university_id)

    if hasattr(user, "universities"):
        ids |= set(user.universities.values_list("id", flat=True))

    return ids


def ticket_queryset_for_user(user):
    """
    Returns scoped queryset for support tickets.
    """

    qs = (
        SupportTicket.objects
        .select_related("created_by", "assigned_to")
        .annotate(responses_count=Count("responses"))
    )

    role_name = getattr(getattr(user, "role", None), "name", None)

    # Tech support sees all
    if role_name == Role.TECH_SUPPORT:
        return qs

    # University admin sees tickets in his university scope
    if role_name == Role.UNIVERSITY_ADMIN:
        uni_ids = get_user_university_ids(user)

        return qs.filter(
            Q(created_by__university_id__in=uni_ids) |
            Q(created_by__universities__id__in=uni_ids)
        ).distinct()

    # Default: ticket owner only
    return qs.filter(created_by=user)


def responses_queryset_for_user(ticket, user):
    """
    Responses queryset with internal note filtering.
    """

    qs = SupportTicketResponse.objects.filter(
        ticket=ticket
    ).select_related("author")

    role_name = getattr(getattr(user, "role", None), "name", None)

    if role_name != Role.TECH_SUPPORT:
        qs = qs.filter(is_internal=False)

    return qs.order_by("created_at")
