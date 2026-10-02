# medismile/utils/scoping.py
"""
University scoping helpers.

The custom User model has no ``university`` field: a user's university lives on
their role profile (``<role>profile_profile.university``). Code that reads
``user.university_id`` silently gets ``None``, and ``filter(university_id=None)``
turns into ``IS NULL`` — i.e. it matches *unscoped* rows instead of nothing.
Always resolve the university through these helpers.
"""
from django.core.exceptions import ObjectDoesNotExist

_PROFILE_ATTRS_BY_ROLE = {
    "patient": "patientprofile_profile",
    "student": "studentprofile_profile",
    "supervisor": "supervisorprofile_profile",
    "university_admin": "universityadminprofile_profile",
}


def get_user_university_id(user):
    """
    Return the university id bound to ``user`` through their role profile,
    or ``None`` when the user has no role, no profile or no university.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return None
    role_name = getattr(getattr(user, "role", None), "name", None)
    attr = _PROFILE_ATTRS_BY_ROLE.get(role_name)
    if not attr:
        return None
    try:
        profile = getattr(user, attr)
    except (AttributeError, ObjectDoesNotExist):
        return None
    return getattr(profile, "university_id", None)


def same_university(user, university_id) -> bool:
    """
    True only when both sides are known and equal. ``None`` never matches,
    so unscoped objects are not visible through university-level access.
    """
    user_university_id = get_user_university_id(user)
    return bool(user_university_id and university_id and user_university_id == university_id)
