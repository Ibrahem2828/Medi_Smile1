from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Content, ContentLike, ContentComment


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    """
    Admin configuration for Community Content.
    """

    list_display = (
        "id",
        "title",
        "content_type",
        "category",
        "author",
        "university",
        "status",
        "is_public",
        "is_featured",
        "created_at",
    )

    list_filter = (
        "status",
        "content_type",
        "category",
        "is_public",
        "is_featured",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "author__email",
        "author__username",
    )

    readonly_fields = (
        "id",
        "author",
        "approved_by",
        "approved_at",
        "view_count",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (_("Basic Information"), {
            "fields": (
                "title",
                "description",
                "content_type",
                "category",
                "file",
                "url",
                "tags",
            )
        }),
        (_("Visibility"), {
            "fields": (
                "is_public",
                "is_featured",
                "university",
            )
        }),
        (_("Moderation"), {
            "fields": (
                "status",
                "approved_by",
                "approved_at",
                "rejection_reason",
            )
        }),
        (_("System"), {
            "fields": (
                "author",
                "view_count",
                "created_at",
                "updated_at",
            )
        }),
    )


@admin.register(ContentLike)
class ContentLikeAdmin(admin.ModelAdmin):
    """
    Admin configuration for Content Likes.
    """

    list_display = (
        "id",
        "content",
        "user",
        "created_at",
    )

    search_fields = (
        "content__title",
        "user__username",
        "user__email",
    )

    readonly_fields = (
        "id",
        "created_at",
    )


@admin.register(ContentComment)
class ContentCommentAdmin(admin.ModelAdmin):
    """
    Admin configuration for Content Comments.
    """

    list_display = (
        "id",
        "content",
        "user",
        "is_approved",
        "created_at",
    )

    list_filter = (
        "is_approved",
        "created_at",
    )

    search_fields = (
        "content__title",
        "user__username",
        "text",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )
