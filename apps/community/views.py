# apps/community/views.py
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from medismile.utils.auth import resolve_request_user
from apps.accounts.models import User, Role

from .models import Content
from .permissions import (
    CanCreateContent,
    CanViewContent,
    CanModerateContent,
    CanLikeContent,
    CanCommentContent,
)
from .selectors import (
    content_queryset_for_user,
    pending_content_for_moderator,
    student_public_rating,
)
from .services import (
    create_content,
    approve_content,
    reject_content,
    toggle_like,
    add_comment,
)
from .serializers import (
    ContentSerializer,
    ContentCreateSerializer,
    ContentRejectSerializer,
    ContentCommentSerializer,
    ContentCommentCreateSerializer,
    ToggleLikeResponseSerializer,
    StudentPublicRatingSerializer,
)


class ContentViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ContentSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)
        return content_queryset_for_user(user)

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), CanCreateContent()]
        if self.action == "retrieve":
            return [IsAuthenticated(), CanViewContent()]
        if self.action in {"pending", "approve", "reject"}:
            return [IsAuthenticated(), CanModerateContent()]
        if self.action == "like":
            return [IsAuthenticated(), CanLikeContent()]
        if self.action == "comment":
            return [IsAuthenticated(), CanCommentContent()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return ContentCreateSerializer
        if self.action == "reject":
            return ContentRejectSerializer
        if self.action == "comment":
            return ContentCommentCreateSerializer
        return ContentSerializer

    # ---------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------

    def list(self, request):
        qs = self.get_queryset()
        return Response(ContentSerializer(qs, many=True).data)

    def retrieve(self, request, pk=None):
        content = self.get_object()
        self.check_object_permissions(request, content)
        return Response(ContentSerializer(content).data)

    def create(self, request):
        user = resolve_request_user(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        content = create_content(author=user, data=serializer.validated_data)
        return Response(ContentSerializer(content).data, status=status.HTTP_201_CREATED)

    # ---------------------------------------------------------
    # Moderation
    # ---------------------------------------------------------

    @action(detail=False, methods=["get"])
    def pending(self, request):
        user = resolve_request_user(request)
        qs = pending_content_for_moderator(user)
        return Response(ContentSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        content = Content.objects.get(pk=pk)
        self.check_object_permissions(request, content)

        user = resolve_request_user(request)
        content = approve_content(moderator=user, content=content)
        return Response(ContentSerializer(content).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        content = Content.objects.get(pk=pk)
        self.check_object_permissions(request, content)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = resolve_request_user(request)
        content = reject_content(
            moderator=user,
            content=content,
            reason=serializer.validated_data["reason"],
        )
        return Response(ContentSerializer(content).data)

    # ---------------------------------------------------------
    # Interactions
    # ---------------------------------------------------------

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        content = Content.objects.get(pk=pk)
        user = resolve_request_user(request)

        liked = toggle_like(user=user, content=content)
        return Response(ToggleLikeResponseSerializer({"liked": liked}).data)

    @action(detail=True, methods=["post"])
    def comment(self, request, pk=None):
        content = Content.objects.get(pk=pk)
        user = resolve_request_user(request)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = add_comment(
            user=user,
            content=content,
            text=serializer.validated_data["text"],
        )
        return Response(ContentCommentSerializer(comment).data, status=status.HTTP_201_CREATED)


# ============================================================
# ⭐ Student Public Rating API
# ============================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_public_rating_view(request, student_id):
    try:
        student = User.objects.get(id=student_id, role__name=Role.STUDENT)
    except User.DoesNotExist:
        return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

    data = student_public_rating(student)
    return Response(StudentPublicRatingSerializer(data).data)
