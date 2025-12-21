# apps/universities/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import University, Faculty, AcademicProgram, AcademicYear


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "short_name",
        "city",
        "country",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "country", "city")
    search_fields = ("name", "short_name", "email")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("name",)

    fieldsets = (
        (_("Basic Information"), {
            "fields": (
                "id",
                "name",
                "short_name",
                "description",
                "logo",
            )
        }),
        (_("Contact Information"), {
            "fields": (
                "address",
                "city",
                "country",
                "email",
                "phone",
                "website",
            )
        }),
        (_("Status & Metadata"), {
            "fields": (
                "is_active",
                "created_at",
                "updated_at",
            )
        }),
    )

    def has_delete_permission(self, request, obj=None):
        # Prevent hard delete to preserve institutional history
        return False


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "university",
        "is_active",
        "created_at",
    )
    list_filter = ("university", "is_active")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at")
    ordering = ("name",)


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
    list_filter = ("level", "university", "faculty", "is_active")
    search_fields = ("name", "code")
    readonly_fields = ("id", "created_at")
    ordering = ("name",)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "university",
        "start_date",
        "end_date",
        "is_active",
    )
    list_filter = ("university", "is_active")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at")
    ordering = ("-start_date",)
