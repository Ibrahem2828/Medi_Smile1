import logging

# apps/accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from .models import (
    User,
    Role,
    PatientProfile,
    StudentProfile,
    SupervisorProfile,
    UniversityAdminProfile,
    TechSupportProfile,
)

logger = logging.getLogger(__name__)


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

    try:
        if role_name == Role.PATIENT:
            PatientProfile.objects.get_or_create(user=instance)

        elif role_name == Role.STUDENT:
            desired_university_id = getattr(instance, "_desired_university_id", None)
            if not desired_university_id:
                logger.warning("Student profile skipped: missing desired_university_id")
                return

            profile, _ = StudentProfile.objects.get_or_create(
                user=instance,
                defaults={"university_id": desired_university_id},
            )
            if profile.university_id != desired_university_id:
                profile.university_id = desired_university_id
                profile.full_clean()
                profile.save(update_fields=["university"])

        elif role_name == Role.SUPERVISOR:
            desired_university_id = getattr(instance, "_desired_university_id", None)
            if not desired_university_id:
                logger.warning("Supervisor profile skipped: missing desired_university_id")
                return

            profile, _ = SupervisorProfile.objects.get_or_create(
                user=instance,
                defaults={"university_id": desired_university_id},
            )
            if profile.university_id != desired_university_id:
                profile.university_id = desired_university_id
                profile.full_clean()
                profile.save(update_fields=["university"])

        elif role_name == Role.UNIVERSITY_ADMIN:
            desired_university_id = getattr(instance, "_desired_university_id", None)
            if not desired_university_id:
                logger.warning("University Admin profile skipped: missing desired_university_id")
                return

            profile, _ = UniversityAdminProfile.objects.get_or_create(
                user=instance,
                defaults={"university_id": desired_university_id},
            )
            if profile.university_id != desired_university_id:
                profile.university_id = desired_university_id
                profile.full_clean()
                profile.save(update_fields=["university"])

        elif role_name == Role.TECH_SUPPORT:
            TechSupportProfile.objects.get_or_create(user=instance)

    except ValidationError as exc:
        # Fail-safe: لا نكسر إنشاء المستخدم بسبب أخطاء بيانات ثانوية
        logger.error("Profile creation validation error for user %s: %s", instance.id, exc)
    except Exception:
        logger.exception("Profile creation failed for user %s", instance.id)


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

    try:
        profile_model.objects.get_or_create(user=instance)
    except ValidationError as exc:
        logger.error("Profile ensure failed for user %s: %s", instance.id, exc)
    except Exception:
        logger.exception("Profile ensure failed for user %s", instance.id)
