# apps/community/views.py
import logging
from rest_framework import status, viewsets, serializers as drf_serializers
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

logger = logging.getLogger(__name__)


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
        try:
            qs = self.get_queryset()
            return Response({"status": "success", "data": ContentSerializer(qs, many=True).data})
        except Exception as exc:
            logger.exception("Community list failed", exc_info=exc)
            return Response(
                {"status": "error", "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.", "errors": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, pk=None):
        try:
            content = self.get_object()
            self.check_object_permissions(request, content)
            return Response({"status": "success", "data": ContentSerializer(content).data})
        except drf_serializers.ValidationError as exc:
            return Response({"status": "error", "message": "Invalid request.", "errors": exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Community retrieve failed", exc_info=exc)
            return Response(
                {"status": "error", "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.", "errors": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def create(self, request):
        try:
            user = resolve_request_user(request)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            content = create_content(author=user, data=serializer.validated_data)
            return Response({"status": "success", "data": ContentSerializer(content).data}, status=status.HTTP_201_CREATED)
        except drf_serializers.ValidationError as exc:
            return Response({"status": "error", "message": "Invalid request.", "errors": exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as exc:
            return Response({"status": "error", "message": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            logger.exception("Community create failed", exc_info=exc)
            return Response(
                {"status": "error", "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.", "errors": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # ---------------------------------------------------------
    # Moderation
    # ---------------------------------------------------------

    @action(detail=False, methods=["get"])
    def pending(self, request):
        try:
            user = resolve_request_user(request)
            qs = pending_content_for_moderator(user)
            return Response({"status": "success", "data": ContentSerializer(qs, many=True).data})
        except Exception as exc:
            logger.exception("Community pending failed", exc_info=exc)
            return Response(
                {"status": "error", "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.", "errors": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        try:
            content = self.get_object()
            self.check_object_permissions(request, content)

            user = resolve_request_user(request)
            content = approve_content(moderator=user, content=content)
            return Response({"status": "success", "data": ContentSerializer(content).data})
        except drf_serializers.ValidationError as exc:
            return Response({"status": "error", "message": "Invalid request.", "errors": exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Community approve failed", exc_info=exc)
            return Response(
                {"status": "error", "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.", "errors": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        try:
            content = self.get_object()
            self.check_object_permissions(request, content)

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = resolve_request_user(request)
            content = reject_content(
                moderator=user,
                content=content,
                reason=serializer.validated_data["reason"],
            )
            return Response({"status": "success", "data": ContentSerializer(content).data})
        except drf_serializers.ValidationError as exc:
            return Response({"status": "error", "message": "Invalid request.", "errors": exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Community reject failed", exc_info=exc)
            return Response(
                {"status": "error", "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.", "errors": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # ---------------------------------------------------------
    # Interactions
    # ---------------------------------------------------------

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        try:
            content = self.get_object()
            user = resolve_request_user(request)

            liked = toggle_like(user=user, content=content)
            return Response({"status": "success", "data": ToggleLikeResponseSerializer({"liked": liked}).data})
        except drf_serializers.ValidationError as exc:
            return Response({"status": "error", "message": "Invalid request.", "errors": exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Community like failed", exc_info=exc)
            return Response(
                {"status": "error", "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.", "errors": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def comment(self, request, pk=None):
        try:
            content = self.get_object()
            user = resolve_request_user(request)

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            comment = add_comment(
                user=user,
                content=content,
                text=serializer.validated_data["text"],
            )
            return Response({"status": "success", "data": ContentCommentSerializer(comment).data}, status=status.HTTP_201_CREATED)
        except drf_serializers.ValidationError as exc:
            return Response({"status": "error", "message": "Invalid request.", "errors": exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Community comment failed", exc_info=exc)
            return Response(
                {"status": "error", "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.", "errors": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


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

    try:
        data = student_public_rating(student)
        return Response({"status": "success", "data": StudentPublicRatingSerializer(data).data})
    except Exception as exc:
        logger.exception("Student public rating failed", exc_info=exc)
        return Response(
            {"status": "error", "message": "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.", "errors": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
