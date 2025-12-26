# apps/attachments/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Role

from .models import Attachment
from .serializers import (
    AttachmentSerializer,
    AttachmentCreateSerializer,
)
from .permissions import (
    IsAuthenticatedAndActive,
    CanViewAttachment,
    CanCreateAttachment,
    CanDeleteAttachment,
)


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
        role = user.role.name

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
            university = user.universityadminprofile_profile.university
            return base_qs.filter(case__university=university)

        return Attachment.objects.none()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AttachmentCreateSerializer
        return AttachmentSerializer

    def perform_create(self, serializer):
        serializer.save(context={"request": self.request})


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
