"""
Shared admin mixins for consistent, optimized admin configuration.
"""

from django.contrib import admin


class BaseOptimizedAdmin(admin.ModelAdmin):
    """
    Provides:
    - save_on_top for quicker actions
    - list_per_page and show_full_result_count tuned for performance
    - auto read-only for id/created_at/updated_at when present
    - auto date_hierarchy on created_at if not explicitly set
    - auto list_select_related for FK/OneToOne unless overridden
    """

    save_on_top = True
    list_per_page = 50
    show_full_result_count = False
    list_max_show_all = 200

    auto_readonly_fields = ("id", "created_at", "updated_at")
    auto_date_hierarchy_fields = ("created_at", "created", "date_created")
    select_related_fields: tuple[str, ...] = ()

    def get_readonly_fields(self, request, obj=None):
        fields = set(super().get_readonly_fields(request, obj))
        model_fields = {f.name for f in self.model._meta.fields}
        fields.update(f for f in self.auto_readonly_fields if f in model_fields)
        return tuple(fields)

    def get_date_hierarchy(self, request):
        if self.date_hierarchy:
            return self.date_hierarchy
        model_fields = {f.name for f in self.model._meta.fields}
        for field in self.auto_date_hierarchy_fields:
            if field in model_fields:
                return field
        return None

    def get_list_select_related(self, request):
        if self.select_related_fields:
            return self.select_related_fields
        related_fields = [
            f.name for f in self.model._meta.fields if f.many_to_one or f.one_to_one
        ]
        return tuple(related_fields)
