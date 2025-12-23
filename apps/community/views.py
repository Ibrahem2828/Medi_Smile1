from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Content, ContentLike, ContentComment
from .serializers import (
    ContentSerializer,
    ContentCreateSerializer,
    ContentUpdateSerializer,
    ContentCommentSerializer,
    ContentCommentCreateSerializer,
)

from apps.accounts.permissions import (
    IsStudent,
    IsSupervisor,
    IsUniversityAdmin,
)
from medismile.utils.auth import resolve_request_user, require_request_user


# ============================================================
# Content List & Create
# ============================================================

class ContentListView(generics.ListCreateAPIView):
    """
    Community content list & creation.

    Visibility rules:
    - Public approved content: visible to everyone
    - Student: sees own pending / rejected content
    - Supervisor / Admin: see approved public content only here
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = resolve_request_user(self.request)

        qs = Content.objects.select_related(
            "author",
            "approved_by",
            "university",
        ).prefetch_related(
            "likes",
            "comments",
        )

        # Base: approved + public
        queryset = qs.filter(is_public=True, status=Content.Status.APPROVED)

        # Student sees his own drafts
        if user and user.role == "student":
            queryset = qs.filter(
                Q(is_public=True, status=Content.Status.APPROVED)
                | Q(author=user)
            )

        # Filters
        params = self.request.query_params

        if params.get("type"):
            queryset = queryset.filter(content_type=params["type"])

        if params.get("category"):
            queryset = queryset.filter(category=params["category"])

        if params.get("university"):
            queryset = queryset.filter(university_id=params["university"])

        if params.get("featured") == "true":
            queryset = queryset.filter(is_featured=True)

        # Student-only status filter (own content)
        if params.get("status") and user and user.role == "student":
            queryset = queryset.filter(author=user, status=params["status"])

        # Ordering whitelist
        order_by = params.get("order_by", "-created_at")
        if order_by in {
            "created_at", "-created_at",
            "view_count", "-view_count",
            "title", "-title",
        }:
            queryset = queryset.order_by(order_by)

        return queryset

    def get_serializer_class(self):
        return ContentCreateSerializer if self.request.method == "POST" else ContentSerializer

    def perform_create(self, serializer):
        """
        Create content.
        If student → send approval notification.
        """
        content = serializer.save()

        if content.author.role == "student" and content.status == Content.Status.PENDING:
            from apps.notifications.utils import create_content_approval_notification
            create_content_approval_notification(content)


# ============================================================
# Content Detail
# ============================================================

class ContentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve / Update / Delete content.

    - View: increments view_count safely
    - Update/Delete:
        * Author: only before approval
        * Supervisor / Admin: anytime
    """

    queryset = Content.objects.select_related(
        "author",
        "approved_by",
        "university",
    )
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return ContentUpdateSerializer if self.request.method in {"PUT", "PATCH"} else ContentSerializer

    def get_permissions(self):
        if self.request.method in {"PUT", "PATCH", "DELETE"}:
            return [IsAuthenticated(), IsStudent() | IsSupervisor() | IsUniversityAdmin()]
        return [IsAuthenticated()]

    def retrieve(self, request, *args, **kwargs):
        """
        Increment view counter atomically.
        """
        instance = self.get_object()
        Content.objects.filter(id=instance.id).update(view_count=Count("view_count") + 1)
        instance.refresh_from_db(fields=["view_count"])

        serializer = self.get_serializer(instance, context={"request": request})
        return Response(serializer.data)


# ============================================================
# Comments
# ============================================================

class ContentCommentListView(generics.ListCreateAPIView):
    """
    List / Create comments.

    Rules:
    - Patient: ❌ cannot comment
    - Student / Supervisor: ✅
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        content_id = self.kwargs["content_id"]
        return ContentComment.objects.select_related("user").filter(
            content_id=content_id,
            is_approved=True,
            parent__isnull=True,
        )

    def get_serializer_class(self):
        return ContentCommentCreateSerializer if self.request.method == "POST" else ContentCommentSerializer

    def perform_create(self, serializer):
        serializer.save(content_id=self.kwargs["content_id"])


# ============================================================
# Likes
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def like_content(request, content_id):
    """
    Toggle like / unlike.
    """

    user, error = require_request_user(request)
    if error:
        return error

    try:
        content = Content.objects.get(
            id=content_id,
            is_public=True,
            status=Content.Status.APPROVED,
        )
    except Content.DoesNotExist:
        return Response({"error": _("Content not found")}, status=status.HTTP_404_NOT_FOUND)

    like, created = ContentLike.objects.get_or_create(
        content=content,
        user=user,
    )

    if not created:
        like.delete()
        return Response({"liked": False}, status=status.HTTP_200_OK)

    return Response({"liked": True}, status=status.HTTP_201_CREATED)


# ============================================================
# Trending Content
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trending_content(request):
    """
    Top content in last 7 days based on views & likes.
    """

    from datetime import timedelta

    week_ago = timezone.now() - timedelta(days=7)

    qs = (
        Content.objects.filter(
            created_at__gte=week_ago,
            is_public=True,
            status=Content.Status.APPROVED,
        )
        .annotate(likes_count=Count("likes"))
        .order_by("-view_count", "-likes_count")[:10]
    )

    serializer = ContentSerializer(qs, many=True, context={"request": request})
    return Response(serializer.data)


# ============================================================
# Moderation (Supervisor / Admin)
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsSupervisor | IsUniversityAdmin])
def pending_content(request):
    """
    List pending content for moderation.
    """

    user, error = require_request_user(request)
    if error:
        return error

    qs = Content.objects.filter(status=Content.Status.PENDING)

    if user.role == "supervisor" and hasattr(user, "supervisorprofile"):
        if user.supervisorprofile.university:
            qs = qs.filter(university=user.supervisorprofile.university)

    serializer = ContentSerializer(qs, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsSupervisor | IsUniversityAdmin])
@transaction.atomic
def approve_content(request, content_id):
    """
    Approve pending content.
    """

    user, error = require_request_user(request)
    if error:
        return error

    try:
        content = Content.objects.select_for_update().get(
            id=content_id,
            status=Content.Status.PENDING,
        )
    except Content.DoesNotExist:
        return Response({"error": _("Content not found")}, status=status.HTTP_404_NOT_FOUND)

    content.status = Content.Status.APPROVED
    content.approved_by = user
    content.approved_at = timezone.now()
    content.rejection_reason = None
    content.save()

    from apps.notifications.utils import create_content_approved_notification
    create_content_approved_notification(content, user)

    serializer = ContentSerializer(content, context={"request": request})
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsSupervisor | IsUniversityAdmin])
@transaction.atomic
def reject_content(request, content_id):
    """
    Reject pending content.
    """

    user, error = require_request_user(request)
    if error:
        return error

    try:
        content = Content.objects.select_for_update().get(
            id=content_id,
            status=Content.Status.PENDING,
        )
    except Content.DoesNotExist:
        return Response({"error": _("Content not found")}, status=status.HTTP_404_NOT_FOUND)

    reason = request.data.get("rejection_reason", "")

    content.status = Content.Status.REJECTED
    content.approved_by = user
    content.approved_at = timezone.now()
    content.rejection_reason = reason
    content.save()

    from apps.notifications.utils import create_content_rejected_notification
    create_content_rejected_notification(content, user, reason)

    serializer = ContentSerializer(content, context={"request": request})
    return Response(serializer.data)
