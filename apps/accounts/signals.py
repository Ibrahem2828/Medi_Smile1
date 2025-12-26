# apps/accounts/signals.py
from django.db.models.signals import post_save
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
# Auto-create profile on user creation
# ============================================================
@receiver(post_save, sender=User)
def create_user_profile(sender, instance: User, created: bool, **kwargs):
    """
    Automatically create the correct profile based on user role.

    Rules:
    - One profile per user
    - Profile type strictly matches user.role
    - Safe to run multiple times (idempotent)
    """

    if not created or not instance.role:
        return

    role_name = instance.role.name

    if role_name == Role.PATIENT:
        PatientProfile.objects.get_or_create(user=instance)

    elif role_name == Role.STUDENT:
        StudentProfile.objects.get_or_create(user=instance)

    elif role_name == Role.SUPERVISOR:
        SupervisorProfile.objects.get_or_create(user=instance)

    elif role_name == Role.UNIVERSITY_ADMIN:
        UniversityAdminProfile.objects.get_or_create(user=instance)

    elif role_name == Role.TECH_SUPPORT:
        TechSupportProfile.objects.get_or_create(user=instance)


# ============================================================
# Guard: Prevent orphan profiles if role is missing
# ============================================================
@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance: User, **kwargs):
    """
    Safety net:
    - Ensures profile exists if user was created without signals (edge cases).
    - Does NOT create multiple profiles.
    """

    if not instance.role:
        return

    role_name = instance.role.name

    profile_map = {
        Role.PATIENT: PatientProfile,
        Role.STUDENT: StudentProfile,
        Role.SUPERVISOR: SupervisorProfile,
        Role.UNIVERSITY_ADMIN: UniversityAdminProfile,
        Role.TECH_SUPPORT: TechSupportProfile,
    }

    profile_model = profile_map.get(role_name)
    if not profile_model:
        return

    profile_model.objects.get_or_create(user=instance)
