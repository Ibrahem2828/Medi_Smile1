# apps/accounts/models.py
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


# ============================================================
# Role Model (RBAC Core)
# ============================================================
class Role(models.Model):
    """
    Central Role model for RBAC.

    Notes:
    - Role name is controlled by ROLE_CHOICES (stable identifiers used across the project).
    - Permissions are enforced by central Permission Matrix / Checker (not here).
    """

    PATIENT = "patient"
    STUDENT = "student"
    SUPERVISOR = "supervisor"
    UNIVERSITY_ADMIN = "university_admin"
    TECH_SUPPORT = "tech_support"

    ROLE_CHOICES = (
        (PATIENT, _("Patient")),
        (STUDENT, _("Student")),
        (SUPERVISOR, _("Supervisor")),
        (UNIVERSITY_ADMIN, _("University Admin")),
        (TECH_SUPPORT, _("Tech Support")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        unique=True,
        verbose_name=_("Role Name"),
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "roles"
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")
        indexes = [
            models.Index(fields=["name"], name="idx_roles_name"),
        ]

    def __str__(self) -> str:
        return self.name


# ============================================================
# User Model
# ============================================================
class User(AbstractUser):
    """
    Custom user model with UUID PK and RBAC via Role FK.

    Key rules:
    - email is unique and acts as USERNAME_FIELD.
    - role is mandatory.
    - created_by is used for audit and internal flows (created by admin/system).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(_("email address"), unique=True)

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="users",
        verbose_name=_("Role"),
    )

    fcm_token = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("FCM Token"),
    )

    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_users",
        verbose_name=_("Created By"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # keep explicit field here (even though AbstractUser has is_active) for clarity & migrations stability
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    # Resolve reverse relation conflicts
    groups = models.ManyToManyField(
        "auth.Group",
        blank=True,
        related_name="custom_user_groups",
        related_query_name="custom_user",
    )

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        blank=True,
        related_name="custom_user_permissions",
        related_query_name="custom_user",
    )

    class Meta:
        db_table = "users"
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        indexes = [
            models.Index(fields=["email"], name="idx_users_email"),
            models.Index(fields=["role"], name="idx_users_role"),
            models.Index(fields=["is_active"], name="idx_users_active"),
        ]

    @property
    def role_name(self) -> str:
        return getattr(self.role, "name", "")

    def clean(self):
        super().clean()

        if not self.role_id:
            raise ValidationError(_("User must have a role."))

        # normalize email (keeps behavior stable but production-friendly)
        if self.email:
            self.email = self.email.strip().lower()

    def __str__(self) -> str:
        return self.email


# ============================================================
# Base Profile (Abstract)
# ============================================================
class Profile(models.Model):
    """
    Base abstract profile.

    Important:
    - Profiles store data only.
    - Access control is enforced centrally by RBAC (Role + Scope + Ownership + State).
    """

    GENDER_CHOICES = (
        ("male", _("Male")),
        ("female", _("Female")),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="%(class)s_profile",  # keep as-is (do not break existing relations)
    )

    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
    )
    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # enforce model-level validation consistently (production safe)
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        return full_name or str(self.user)


# ============================================================
# Patient Profile
# ============================================================
class PatientProfile(Profile):
    medical_history = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    medications = models.TextField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = "patient_profiles"
        indexes = [
            models.Index(fields=["created_at"], name="idx_patient_prof_created"),
        ]

    def clean(self):
        super().clean()
        # Guard: ensure correct role
        if self.user and self.user.role and self.user.role.name != Role.PATIENT:
            raise ValidationError(_("PatientProfile requires PATIENT role."))


# ============================================================
# Student Profile
# ============================================================
class StudentProfile(Profile):
    university = models.ForeignKey(
        "universities.University",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    student_id = models.CharField(max_length=50, blank=True, null=True)
    year_of_study = models.PositiveIntegerField(blank=True, null=True)
    specialization = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "student_profiles"
        indexes = [
            models.Index(fields=["university"], name="idx_student_prof_univ"),
            models.Index(fields=["student_id"], name="idx_student_prof_sid"),
        ]

    def clean(self):
        super().clean()
        if self.user and self.user.role and self.user.role.name != Role.STUDENT:
            raise ValidationError(_("StudentProfile requires STUDENT role."))
        if not self.university:
            raise ValidationError(_("Student must be linked to a university."))


# ============================================================
# Supervisor Profile
# ============================================================
class SupervisorProfile(Profile):
    university = models.ForeignKey(
        "universities.University",
        on_delete=models.SET_NULL,
        null=True,
        related_name="supervisors",
    )
    department = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    license_number = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "supervisor_profiles"
        indexes = [
            models.Index(fields=["university"], name="idx_supervisor_prof_univ"),
            models.Index(fields=["license_number"], name="idx_supervisor_prof_lic"),
        ]

    def clean(self):
        super().clean()
        if self.user and self.user.role and self.user.role.name != Role.SUPERVISOR:
            raise ValidationError(_("SupervisorProfile requires SUPERVISOR role."))
        if not self.university:
            raise ValidationError(_("Supervisor must be linked to a university."))


# ============================================================
# University Admin Profile
# ============================================================
class UniversityAdminProfile(Profile):
    university = models.ForeignKey(
        "universities.University",
        on_delete=models.SET_NULL,
        null=True,
        related_name="admins",
    )
    department = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "university_admin_profiles"
        indexes = [
            models.Index(fields=["university"], name="idx_univ_admin_prof_univ"),
        ]

    def clean(self):
        super().clean()
        if self.user and self.user.role and self.user.role.name != Role.UNIVERSITY_ADMIN:
            raise ValidationError(_("UniversityAdminProfile requires UNIVERSITY_ADMIN role."))
        if not self.university:
            raise ValidationError(_("University Admin must be linked to a university."))
        if self.pk:
            previous = UniversityAdminProfile.objects.filter(pk=self.pk).values_list("university_id", flat=True).first()
            if previous and previous != self.university_id:
                raise ValidationError(_("University Admin cannot switch to a different university."))


# ============================================================
# Tech Support Profile
# ============================================================
class TechSupportProfile(Profile):
    department = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "tech_support_profiles"
        indexes = [
            models.Index(fields=["created_at"], name="idx_tech_support_prof_created"),
        ]

    def clean(self):
        super().clean()
        if self.user and self.user.role and self.user.role.name != Role.TECH_SUPPORT:
            raise ValidationError(_("TechSupportProfile requires TECH_SUPPORT role."))
