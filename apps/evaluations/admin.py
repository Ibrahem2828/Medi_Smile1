# apps/evaluations/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from medismile.admin_mixins import BaseOptimizedAdmin

from .models import Evaluation, EvaluationAdjustment


@admin.register(Evaluation)
class EvaluationAdmin(BaseOptimizedAdmin):
    list_display = (
        "id",
        "student",
        "evaluator",
        "evaluator_role",
        "target_type",
        "score",
        "final_score",
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
        (_("Evaluation Information"), {"fields": ("id", "university", "status", "target_type", "target_id")}),
        (_("People"), {"fields": ("evaluator", "evaluator_role", "student")}),
        (_("Target"), {"fields": ("case", "session", "appointment")}),
        (_("Evaluation Data"), {"fields": ("score", "final_score", "rubric", "comment")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at", "submitted_at", "finalized_at")}),
    )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EvaluationAdjustment)
class EvaluationAdjustmentAdmin(BaseOptimizedAdmin):
    list_display = (
        "id",
        "evaluation",
        "adjusted_by",
        "adjusted_role",
        "old_score",
        "new_score",
        "adjusted_at",
    )
    list_filter = ("adjusted_role", "adjusted_at")
    search_fields = (
        "evaluation__id",
        "adjusted_by__username",
        "adjusted_by__email",
    )
    readonly_fields = ("id", "adjusted_at")
    ordering = ("-adjusted_at",)
