# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import (
    Role,
    User,
    PatientProfile,
    StudentProfile,
    SupervisorProfile,
    UniversityAdminProfile,
    TechSupportProfile,
)

# ============================================================
# Role Admin
# ============================================================
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Admin configuration for Role model (RBAC core).
    """
    list_display = ("id", "name", "description", "created_at")
    search_fields = ("name",)
    ordering = ("name",)
    readonly_fields = ("id", "created_at")


# ============================================================
# Profile Inlines (attached to User)
# ============================================================
class PatientProfileInline(admin.StackedInline):
    model = PatientProfile
    can_delete = False
    verbose_name_plural = _("Patient Profile")
    fk_name = "user"


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = _("Student Profile")
    fk_name = "user"


class SupervisorProfileInline(admin.StackedInline):
    model = SupervisorProfile
    can_delete = False
    verbose_name_plural = _("Supervisor Profile")
    fk_name = "user"


class UniversityAdminProfileInline(admin.StackedInline):
    model = UniversityAdminProfile
    can_delete = False
    verbose_name_plural = _("University Admin Profile")
    fk_name = "user"


class TechSupportProfileInline(admin.StackedInline):
    model = TechSupportProfile
    can_delete = False
    verbose_name_plural = _("Tech Support Profile")
    fk_name = "user"


# ============================================================
# User Admin
# ============================================================
@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    Custom User admin with Role (RBAC), audit fields,
    and inline profile management.
    """

    ordering = ("-date_joined",)
    list_display = (
        "id",
        "email",
        "username",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_staff",
        "created_by",
        "date_joined",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "role",
    )
    search_fields = (
        "email",
        "username",
        "first_name",
        "last_name",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "last_login",
        "date_joined",
    )

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (_("Personal info"), {"fields": ("username", "first_name", "last_name")}),
        (
            _("Role & System"),
            {
                "fields": (
                    "role",
                    "fcm_token",
                    "created_by",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Important dates"),
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "first_name",
                    "last_name",
                    "role",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    inlines = [
        PatientProfileInline,
        StudentProfileInline,
        SupervisorProfileInline,
        UniversityAdminProfileInline,
        TechSupportProfileInline,
    ]


# ============================================================
# Profile Admins (standalone access if needed)
# ============================================================
@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "gender", "date_of_birth", "created_at")
    search_fields = ("user__email", "user__username", "user__first_name", "user__last_name")
    list_select_related = ("user",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "university", "student_id", "year_of_study", "created_at")
    search_fields = ("user__email", "user__username", "student_id")
    list_select_related = ("user", "university")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(SupervisorProfile)
class SupervisorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "university", "department", "position", "created_at")
    search_fields = ("user__email", "user__username", "department", "position")
    list_select_related = ("user", "university")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(UniversityAdminProfile)
class UniversityAdminProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "university", "department", "position", "created_at")
    search_fields = ("user__email", "user__username", "department", "position")
    list_select_related = ("user", "university")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(TechSupportProfile)
class TechSupportProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "department", "position", "created_at")
    search_fields = ("user__email", "user__username", "department", "position")
    list_select_related = ("user",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
