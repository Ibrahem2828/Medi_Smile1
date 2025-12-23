# apps/attachments/urls.py

from django.urls import path
from . import views

app_name = "attachments"

urlpatterns = [

    # ============================================================
    # Attachments (List / Upload)
    # ============================================================
    # GET  : list attachments (filtered by case_session_id)
    # POST : upload attachment (student only)
    path(
        "",
        views.AttachmentListView.as_view(),
        name="attachment-list",
    ),

    # ============================================================
    # Attachment Detail
    # ============================================================
    # GET    : retrieve attachment metadata
    # DELETE : delete attachment (student only, before approval)
    path(
        "<uuid:pk>/",
        views.AttachmentDetailView.as_view(),
        name="attachment-detail",
    ),

    # ============================================================
    # File Actions
    # ============================================================
    # Download attachment
    path(
        "<uuid:attachment_id>/download/",
        views.download_attachment,
        name="attachment-download",
    ),

    # Preview image attachment (images only)
    path(
        "<uuid:attachment_id>/preview/",
        views.preview_attachment,
        name="attachment-preview",
    ),
]
