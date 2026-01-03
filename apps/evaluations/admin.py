# apps/evaluations/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from medismile.admin_mixins import BaseOptimizedAdmin

from .models import Evaluation


@admin.register(Evaluation)
class EvaluationAdmin(BaseOptimizedAdmin):
    list_display = (
        "id",
        "student",
        "evaluator",
        "target_type",
        "score",
        "status",
        "university",
        "created_at",
    )

    list_filter = ("status", "target_type", "university", "created_at")
    search_fields = (
        "student__username",
        "student__email",
        "evaluator__username",
        "evaluator__email",
        "comment",
    )

    readonly_fields = ("id", "created_at", "updated_at", "submitted_at", "finalized_at")
    ordering = ("-created_at",)
    list_select_related = ("student", "evaluator", "university")

    fieldsets = (
        (_("Evaluation Information"), {"fields": ("id", "university", "status", "target_type")}),
        (_("People"), {"fields": ("evaluator", "student")}),
        (_("Target"), {"fields": ("case", "session", "appointment")}),
        (_("Evaluation Data"), {"fields": ("score", "rubric", "comment")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at", "submitted_at", "finalized_at")}),
    )

    def has_delete_permission(self, request, obj=None):
        return False
