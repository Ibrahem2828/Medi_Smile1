# apps/attachments/urls.py
from django.urls import path

from .views import (
    AttachmentListCreateView,
    AttachmentDetailView,
    AttachmentFileView,
)

urlpatterns = [
    # =====================================================
    # Attachments
    # =====================================================
    path(
        "",
        AttachmentListCreateView.as_view(),
        name="attachment-list-create",
    ),
    path(
        "<uuid:pk>/file/",
        AttachmentFileView.as_view(),
        name="attachment-file",
    ),
    path(
        "<uuid:pk>/",
        AttachmentDetailView.as_view(),
        name="attachment-detail",
    ),
]
