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
# ROLE ADMIN
# ============================================================
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at")
    search_fields = ("name",)
    ordering = ("name",)
    readonly_fields = ("created_at",)


# ============================================================
# PROFILE INLINES
# ============================================================
class BaseProfileInline(admin.StackedInline):
    extra = 0
    can_delete = False
    verbose_name_plural = _("Profile")


class PatientProfileInline(BaseProfileInline):
    model = PatientProfile


class StudentProfileInline(BaseProfileInline):
    model = StudentProfile


class SupervisorProfileInline(BaseProfileInline):
    model = SupervisorProfile


class UniversityAdminProfileInline(BaseProfileInline):
    model = UniversityAdminProfile


class TechSupportProfileInline(BaseProfileInline):
    model = TechSupportProfile


# ============================================================
# USER ADMIN
# ============================================================
@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    Central User admin.
    Roles and profiles are managed here in a controlled way.
    """

    list_display = (
        "email",
        "username",
        "role",
        "is_active",
        "is_staff",
        "created_by",
        "date_joined",
    )
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-date_joined",)

    readonly_fields = (
        "last_login",
        "date_joined",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal Info"), {"fields": ("username", "first_name", "last_name")}),
        (
            _("Role & Ownership"),
            {
                "fields": (
                    "role",
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
                )
            },
        ),
        (
            _("Important Dates"),
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
