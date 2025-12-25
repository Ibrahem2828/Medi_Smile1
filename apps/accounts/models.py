import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


# ============================================================
# Role Model (RBAC Core)
# ============================================================
class Role(models.Model):
    """
    Central Role model for RBAC.
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
    Custom user model with UUID PK and RBAC via Role FK.
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

    def clean(self):
        super().clean()

        if not self.role:
            raise ValidationError(_("User must have a role."))

    def __str__(self):
        return self.email


# ============================================================
# Base Profile (Abstract)
# ============================================================
class Profile(models.Model):
    """
    Base abstract profile.
    Profiles store data only – permissions come from Role.
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

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


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

    def clean(self):
        super().clean()
        if self.user.role.name != Role.PATIENT:
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

    def clean(self):
        super().clean()
        if self.user.role.name != Role.STUDENT:
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

    def clean(self):
        super().clean()
        if self.user.role.name != Role.SUPERVISOR:
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

    def clean(self):
        super().clean()
        if self.user.role.name != Role.UNIVERSITY_ADMIN:
            raise ValidationError(_("UniversityAdminProfile requires UNIVERSITY_ADMIN role."))
        if not self.university:
            raise ValidationError(_("University Admin must be linked to a university."))


# ============================================================
# Tech Support Profile
# ============================================================
class TechSupportProfile(Profile):
    department = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "tech_support_profiles"

    def clean(self):
        super().clean()
        if self.user.role.name != Role.TECH_SUPPORT:
            raise ValidationError(_("TechSupportProfile requires TECH_SUPPORT role."))
