# apps/attachments/views.py

from __future__ import annotations

from django.db import transaction
from django.http import Http404, HttpResponse
from django.utils.translation import gettext_lazy as _

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from medismile.utils.auth import resolve_request_user

from apps.cases.models import CaseSession
from .models import Attachment
from .serializers import (
    AttachmentSerializer,
    AttachmentCreateSerializer,
)
from .storage_backends import get_storage_backend


# ============================================================
# Internal helpers
# ============================================================

def _user_can_access_attachment(user, attachment: Attachment) -> bool:
    """
    Centralized access control for attachments.
    """

    if not user:
        return False

    session = attachment.case_session
    case = session.case

    if user.role == "patient":
        return case.patient == user

    if user.role == "student":
        return session.student == user

    if user.role == "supervisor":
        return session.supervisor == user

    if user.role in ["university_admin", "tech_support"]:
        return True

    return False


def _user_can_delete_attachment(user, attachment: Attachment) -> bool:
    """
    Only student can delete,
    and only BEFORE session approval.
    """

    if not user or user.role != "student":
        return False

    if attachment.case_session.student != user:
        return False

    if attachment.case_session.status == CaseSession.Status.APPROVED:
        return False

    return True


# ============================================================
# List & Upload Attachments
# ============================================================

class AttachmentListView(generics.ListCreateAPIView):
    """
    - GET:
        List attachments scoped by role & session
    - POST:
        Upload attachment (student only)
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = resolve_request_user(self.request)
        session_id = self.request.query_params.get("case_session_id")

        qs = Attachment.objects.select_related(
            "case_session",
            "uploaded_by",
        ).order_by("-created_at")

        if session_id:
            qs = qs.filter(case_session_id=session_id)

        if not user:
            return Attachment.objects.none()

        if user.role == "patient":
            return qs.filter(case_session__case__patient=user)

        if user.role == "student":
            return qs.filter(case_session__student=user)

        if user.role == "supervisor":
            return qs.filter(case_session__supervisor=user)

        if user.role in ["university_admin", "tech_support"]:
            return qs

        return Attachment.objects.none()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AttachmentCreateSerializer
        return AttachmentSerializer

    def perform_create(self, serializer):
        """
        Creation rules are fully enforced inside serializer.
        """
        serializer.save()


# ============================================================
# Retrieve & Delete Attachment
# ============================================================

class AttachmentDetailView(generics.RetrieveDestroyAPIView):
    """
    - GET: retrieve attachment metadata
    - DELETE: student only (before approval)
    """

    queryset = Attachment.objects.select_related(
        "case_session",
        "uploaded_by",
    )
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        user = resolve_request_user(self.request)

        if not _user_can_access_attachment(user, obj):
            raise Http404(_("Attachment not found"))

        return obj

    def perform_destroy(self, instance):
        user = resolve_request_user(self.request)

        if not _user_can_delete_attachment(user, instance):
            raise Http404(_("You do not have permission to delete this attachment"))

        storage = get_storage_backend()
        storage.delete(instance.file_path)
        instance.delete()


# ============================================================
# Download Attachment
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_attachment(request, attachment_id):
    """
    Download attachment file.
    """

    try:
        attachment = Attachment.objects.select_related(
            "case_session",
            "uploaded_by",
        ).get(id=attachment_id)
    except Attachment.DoesNotExist:
        return Response(
            {"error": _("Attachment not found")},
            status=status.HTTP_404_NOT_FOUND,
        )

    user = resolve_request_user(request)
    if not _user_can_access_attachment(user, attachment):
        return Response(
            {"error": _("Access denied")},
            status=status.HTTP_403_FORBIDDEN,
        )

    storage = get_storage_backend()
    if not storage.exists(attachment.file_path):
        return Response(
            {"error": _("File not found")},
            status=status.HTTP_404_NOT_FOUND,
        )

    file_content = storage.storage.open(attachment.file_path, "rb")

    response = HttpResponse(
        file_content,
        content_type=attachment.mime_type,
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{attachment.original_filename}"'
    )
    return response


# ============================================================
# Preview Attachment (Images Only)
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def preview_attachment(request, attachment_id):
    """
    Preview image attachment.
    """

    try:
        attachment = Attachment.objects.select_related(
            "case_session",
            "uploaded_by",
        ).get(id=attachment_id)
    except Attachment.DoesNotExist:
        return Response(
            {"error": _("Attachment not found")},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not attachment.is_image():
        return Response(
            {"error": _("Attachment is not an image")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = resolve_request_user(request)
    if not _user_can_access_attachment(user, attachment):
        return Response(
            {"error": _("Access denied")},
            status=status.HTTP_403_FORBIDDEN,
        )

    storage = get_storage_backend()
    if not storage.exists(attachment.file_path):
        return Response(
            {"error": _("File not found")},
            status=status.HTTP_404_NOT_FOUND,
        )

    file_content = storage.storage.open(attachment.file_path, "rb")

    return HttpResponse(
        file_content,
        content_type=attachment.mime_type,
    )
