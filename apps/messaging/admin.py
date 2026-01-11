from django.contrib import admin

from medismile.admin_mixins import BaseOptimizedAdmin

from .models import Room, Message


# ============================================================
# Room Admin (Read-only, Audit-style)
# ============================================================

@admin.register(Room)
class RoomAdmin(BaseOptimizedAdmin):
    list_display = (
        "id",
        "thread_type",
        "case",
        "course",
        "participant_patient",
        "participant_student",
        "participant_supervisor",
        "created_at",
    )
    list_filter = ("created_at",)

    readonly_fields = (
        "id",
        "thread_type",
        "case",
        "course",
        "participant_patient",
        "participant_student",
        "participant_supervisor",
        "created_at",
    )

    search_fields = (
        "participant_patient__first_name",
        "participant_patient__last_name",
        "participant_patient__email",
        "participant_student__first_name",
        "participant_student__last_name",
        "participant_student__email",
        "participant_supervisor__first_name",
        "participant_supervisor__last_name",
        "participant_supervisor__email",
        "case__title",
        "course__name",
    )

    ordering = ("-created_at",)
    autocomplete_fields = ("case", "course", "participant_patient", "participant_student", "participant_supervisor")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================
# Message Admin
# ============================================================

@admin.register(Message)
class MessageAdmin(BaseOptimizedAdmin):
    list_display = (
        "id",
        "room",
        "sender",
        "is_system",
        "sent_at",
    )
    list_filter = ("is_system", "sent_at")

    readonly_fields = (
        "id",
        "room",
        "sender",
        "content",
        "is_system",
        "sent_at",
    )

    ordering = ("-sent_at",)
    search_fields = ("content", "sender__email", "room__case__title")
    autocomplete_fields = ("room", "sender")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
