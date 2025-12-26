# apps/attachments/urls.py
from django.urls import path

from .views import (
    AttachmentListCreateView,
    AttachmentDetailView,
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
        "<uuid:pk>/",
        AttachmentDetailView.as_view(),
        name="attachment-detail",
    ),
]
