# apps/universities/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    University,
    Faculty,
    AcademicProgram,
    AcademicYear,
)


# ============================================================
# University Admin (System Level)
# ============================================================
@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "short_name",
        "email",
        "phone",
        "city",
        "country",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "country")
    search_fields = ("name", "short_name", "city", "country", "email", "phone")
    ordering = ("name",)

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "short_name", "is_active")}),
        (
            _("Contact & Location"),
            {
                "fields": (
                    "address",
                    "city",
                    "country",
                    "email",
                    "phone",
                    "website",
                )
            },
        ),
        (_("Branding"), {"fields": ("logo",)}),
        (
            _("System"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


# ============================================================
# Faculty Admin
# ============================================================
@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "university",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "university")
    search_fields = ("name", "university__name")
    ordering = ("university__name", "name")

    readonly_fields = ("created_at",)

    fieldsets = (
        (None, {"fields": ("university", "name", "is_active")}),
        (_("Description"), {"fields": ("description",)}),
        (_("System"), {"fields": ("created_at",)}),
    )


# ============================================================
# Academic Program Admin
# ============================================================
@admin.register(AcademicProgram)
class AcademicProgramAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "level",
        "university",
        "faculty",
        "is_active",
        "created_at",
    )
    list_filter = ("level", "is_active", "university")
    search_fields = ("name", "code", "university__name")
    ordering = ("university__name", "name")

    readonly_fields = ("created_at",)

    fieldsets = (
        (None, {"fields": ("university", "faculty", "name", "code")}),
        (
            _("Academic Info"),
            {
                "fields": (
                    "level",
                    "duration_years",
                    "description",
                )
            },
        ),
        (_("Status"), {"fields": ("is_active",)}),
        (_("System"), {"fields": ("created_at",)}),
    )


# ============================================================
# Academic Year Admin
# ============================================================
@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "university",
        "start_date",
        "end_date",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "university")
    search_fields = ("name", "university__name")
    ordering = ("-start_date",)

    readonly_fields = ("created_at",)

    fieldsets = (
        (None, {"fields": ("university", "name", "is_active")}),
        (
            _("Date Range"),
            {
                "fields": (
                    "start_date",
                    "end_date",
                )
            },
        ),
        (_("System"), {"fields": ("created_at",)}),
    )
