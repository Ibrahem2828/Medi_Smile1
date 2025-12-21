from django.urls import path
from . import views

app_name = "community"

urlpatterns = [

    # =========================================================
    # Content (Public & User Scope)
    # =========================================================

    # List content / Create new content
    path(
        "",
        views.ContentListView.as_view(),
        name="content-list",
    ),

    # Retrieve / Update / Delete single content
    path(
        "<uuid:pk>/",
        views.ContentDetailView.as_view(),
        name="content-detail",
    ),

    # =========================================================
    # Content Interactions
    # =========================================================

    # Like / Unlike content
    path(
        "<uuid:content_id>/like/",
        views.like_content,
        name="content-like",
    ),

    # Comments (list / create)
    path(
        "<uuid:content_id>/comments/",
        views.ContentCommentListView.as_view(),
        name="content-comments",
    ),

    # =========================================================
    # Discovery
    # =========================================================

    # Trending content
    path(
        "trending/",
        views.trending_content,
        name="content-trending",
    ),

    # =========================================================
    # Moderation (Supervisor / University Admin)
    # =========================================================

    # List pending content for approval
    path(
        "moderation/pending/",
        views.pending_content,
        name="content-pending",
    ),

    # Approve content
    path(
        "moderation/<uuid:content_id>/approve/",
        views.approve_content,
        name="content-approve",
    ),

    # Reject content
    path(
        "moderation/<uuid:content_id>/reject/",
        views.reject_content,
        name="content-reject",
    ),
]
