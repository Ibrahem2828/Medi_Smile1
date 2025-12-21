# accounts/models.py
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.translation import gettext_lazy as _


# ============================================================
# Role Model (RBAC Core)
# ============================================================
class Role(models.Model):
    """
    Central Role model for RBAC.
    This replaces hard-coded role strings while keeping
    the same role names used across the system.
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

    def __str__(self):
        return self.name


# ============================================================
# User Model
# ============================================================
class User(AbstractUser):
    """
    Custom user model with UUID primary key and Role-based access control.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(_("email address"), unique=True)

    # 🔑 RBAC: Role as FK instead of CharField
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
        help_text=_("Firebase Cloud Messaging token for push notifications"),
    )

    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_users",
        verbose_name=_("Created By"),
        help_text=_("User who created this account (for audit purposes)"),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    # حل تضارب العلاقات العكسية
    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name=_("groups"),
        blank=True,
        help_text=_(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_name="custom_user_groups",
        related_query_name="custom_user",
    )

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name=_("user permissions"),
        blank=True,
        help_text=_("Specific permissions for this user."),
        related_name="custom_user_permissions",
        related_query_name="custom_user",
    )

    class Meta:
        db_table = "users"
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __str__(self):
        return self.email


# ============================================================
# Base Profile (Abstract)
# ============================================================
class Profile(models.Model):
    """
    Base profile model with common fields.
    Profiles hold data only – permissions are handled by Role.
    """

    GENDER_CHOICES = (
        ("male", _("Male")),
        ("female", _("Female")),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="%(class)s_profile",
        verbose_name=_("User"),
    )

    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, blank=True, null=True
    )
    profile_picture = models.ImageField(
        upload_to="profile_pictures/", blank=True, null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


# ============================================================
# Role-specific Profiles
# ============================================================
class PatientProfile(Profile):
    medical_history = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)
    medications = models.TextField(blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = "patient_profiles"
        verbose_name = _("Patient Profile")
        verbose_name_plural = _("Patient Profiles")


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
        verbose_name = _("Student Profile")
        verbose_name_plural = _("Student Profiles")


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
        verbose_name = _("Supervisor Profile")
        verbose_name_plural = _("Supervisor Profiles")


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
        verbose_name = _("University Admin Profile")
        verbose_name_plural = _("University Admin Profiles")


class TechSupportProfile(Profile):
    department = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "tech_support_profiles"
        verbose_name = _("Tech Support Profile")
        verbose_name_plural = _("Tech Support Profiles")
