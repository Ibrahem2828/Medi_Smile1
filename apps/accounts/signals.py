# apps/accounts/signals.py
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import (
    User,
    Role,
    PatientProfile,
    StudentProfile,
    SupervisorProfile,
    UniversityAdminProfile,
    TechSupportProfile,
)


# ============================================================
# Role → Profile mapping
# ============================================================
ROLE_PROFILE_MAP = {
    Role.PATIENT: PatientProfile,
    Role.STUDENT: StudentProfile,
    Role.SUPERVISOR: SupervisorProfile,
    Role.UNIVERSITY_ADMIN: UniversityAdminProfile,
    Role.TECH_SUPPORT: TechSupportProfile,
}


def _create_profile_for_user(user: User) -> None:
    """
    Create the correct profile for a user based on their role.
    This function is safe to call multiple times.
    """
    if not user.role:
        return

    role_name = user.role.name
    profile_model = ROLE_PROFILE_MAP.get(role_name)

    if not profile_model:
        return

    # Ensure only one profile is created (OneToOneField)
    profile_model.objects.get_or_create(user=user)


# ============================================================
# Create profile on user creation
# ============================================================
@receiver(post_save, sender=User)
def create_profile_on_user_creation(sender, instance: User, created: bool, **kwargs):
    """
    Automatically create the appropriate profile when a user is created.
    """
    if not created:
        return

    # Use on_commit to guarantee the user exists in DB
    transaction.on_commit(lambda: _create_profile_for_user(instance))


# ============================================================
# Handle role change (optional but professional)
# ============================================================
@receiver(pre_save, sender=User)
def handle_role_change(sender, instance: User, **kwargs):
    """
    If a user's role changes, ensure the new role's profile exists.
    We do NOT delete old profiles for safety and auditability.
    """
    if not instance.pk:
        return

    try:
        old_user = User.objects.select_related("role").get(pk=instance.pk)
    except User.DoesNotExist:
        return

    old_role = old_user.role.name if old_user.role else None
    new_role = instance.role.name if instance.role else None

    if old_role != new_role and new_role in ROLE_PROFILE_MAP:
        transaction.on_commit(lambda: _create_profile_for_user(instance))
