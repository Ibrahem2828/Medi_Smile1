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
        "case",
        "participant_patient",
        "participant_student",
        "created_at",
    )

    readonly_fields = (
        "id",
        "case",
        "participant_patient",
        "participant_student",
        "created_at",
    )

    search_fields = (
        "participant_patient__first_name",
        "participant_patient__last_name",
        "participant_patient__email",
        "participant_student__first_name",
        "participant_student__last_name",
        "participant_student__email",
    )

    ordering = ("-created_at",)

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

    readonly_fields = (
        "id",
        "room",
        "sender",
        "content",
        "is_system",
        "sent_at",
    )

    ordering = ("-sent_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
