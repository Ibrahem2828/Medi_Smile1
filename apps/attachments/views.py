# apps/attachments/views.py
import logging
from django.http import FileResponse, Http404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS
from rest_framework import serializers as drf_serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema

from apps.accounts.models import Role

from .models import Attachment
from .serializers import (
    AttachmentSerializer,
    AttachmentCreateSerializer,
)
from .storage_backends import get_storage_backend
from .permissions import (
    IsAuthenticatedAndActive,
    CanViewAttachment,
    CanCreateAttachment,
    CanDeleteAttachment,
)

logger = logging.getLogger(__name__)


# ============================================================
# Attachment List & Create
# ============================================================
class AttachmentListCreateView(generics.ListCreateAPIView):
    """
    List & Create Attachments.

    LIST:
    - Scoped by role & ownership
    - Patient sees only visible attachments

    CREATE:
    - Student uploads attachments for his appointment
    """

    permission_classes = [IsAuthenticatedAndActive]

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, "role", None), "name", None)
        if role is None:
            raise PermissionDenied("User role is missing; contact admin.")

        base_qs = Attachment.objects.select_related(
            "case",
            "appointment",
            "uploaded_by",
            "case__university",
        )

        if role == Role.TECH_SUPPORT:
            return base_qs

        if role == Role.STUDENT:
            return base_qs.filter(uploaded_by=user)

        if role == Role.SUPERVISOR:
            return base_qs.filter(case__supervisor=user)

        if role == Role.PATIENT:
            return base_qs.filter(
                case__patient=user,
                is_visible_to_patient=True,
            )

        if role == Role.UNIVERSITY_ADMIN:
            try:
                university = user.universityadminprofile_profile.university
            except Exception:
                raise PermissionDenied("University Admin profile not found.")
            return base_qs.filter(case__university=university)

        return Attachment.objects.none()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AttachmentCreateSerializer
        return AttachmentSerializer

    def perform_create(self, serializer):
        serializer.save()

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticatedAndActive(), CanCreateAttachment()]
        return [IsAuthenticatedAndActive()]

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except drf_serializers.ValidationError as exc:
            return Response(
                {"status": "error", "message": "Invalid request.", "errors": exc.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Failed to create attachment", exc_info=exc)
            return Response(
                {
                    "status": "error",
                    "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.",
                    "errors": None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================
# Attachment Detail & Delete
# ============================================================
class AttachmentDetailView(generics.RetrieveDestroyAPIView):
    """
    Retrieve or Delete Attachment.

    DELETE:
    - Allowed only for the student who uploaded the attachment
    - No hard delete by admin/supervisor (integrity)
    """

    queryset = Attachment.objects.select_related(
        "case",
        "appointment",
        "uploaded_by",
        "case__university",
    )

    permission_classes = [
        IsAuthenticatedAndActive,
        CanViewAttachment,
        CanDeleteAttachment,
    ]

    serializer_class = AttachmentSerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticatedAndActive(), CanViewAttachment()]
        return [
            IsAuthenticatedAndActive(),
            CanViewAttachment(),
            CanDeleteAttachment(),
        ]


class AttachmentFileView(generics.RetrieveAPIView):
    """Serve an attachment only after applying the normal object permission."""

    queryset = Attachment.objects.select_related(
        "case", "appointment", "uploaded_by", "case__university"
    )
    permission_classes = [IsAuthenticatedAndActive, CanViewAttachment]

    @extend_schema(responses={200: OpenApiTypes.BINARY}, tags=["attachments"])
    def get(self, request, *args, **kwargs):
        attachment = self.get_object()
        self.check_object_permissions(request, attachment)
        if not attachment.file:
            raise Http404
        storage = get_storage_backend()
        try:
            file_handle = storage.open(attachment.file.name, "rb")
        except Exception as exc:
            logger.warning("Attachment file unavailable: %s", attachment.id, exc_info=exc)
            raise Http404 from exc
        response = FileResponse(file_handle, content_type=attachment.mime_type)
        response["Content-Disposition"] = f'attachment; filename="{attachment.original_filename}"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
