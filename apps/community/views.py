# apps/community/views.py
import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers as drf_serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from medismile.utils.auth import resolve_request_user
from apps.accounts.models import Role, User

from .models import Content
from .permissions import (
    CanCreateContent,
    CanViewApprovalLogs,
    CanViewContent,
    CanModerateContent,
    CanLikeContent,
    CanCommentContent,
)
from .selectors import (
    approval_logs_for_user,
    content_queryset_for_user,
    pending_content_for_moderator,
    student_public_rating,
)
from .services import (
    add_comment,
    approve_content,
    create_content,
    delete_content,
    reject_content,
    toggle_like,
    update_content,
)
from .serializers import (
    CommunityApprovalLogSerializer,
    ContentCommentCreateSerializer,
    ContentCommentSerializer,
    ContentCreateSerializer,
    ContentRejectSerializer,
    ContentSerializer,
    ContentUpdateSerializer,
    StudentPublicRatingSerializer,
    ToggleLikeResponseSerializer,
)

logger = logging.getLogger(__name__)


class ContentViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ContentSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)
        if self.action == "pending":
            return pending_content_for_moderator(user)
        if self.action in {"partial_update", "update"}:
            return Content.objects.filter(author=user, is_deleted=False)
        if self.action == "destroy":
            return Content.objects.filter(is_deleted=False)
        if self.action in {"approve", "reject"}:
            return Content.objects.filter(is_deleted=False)
        return content_queryset_for_user(user)

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), CanCreateContent()]
        if self.action == "retrieve":
            return [IsAuthenticated(), CanViewContent()]
        if self.action in {"pending", "approve", "reject"}:
            return [IsAuthenticated(), CanModerateContent()]
        if self.action in {"like", "react"}:
            return [IsAuthenticated(), CanLikeContent()]
        if self.action == "comments":
            return [IsAuthenticated(), CanCommentContent()]
        if self.action in {"partial_update", "update", "destroy"}:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return ContentCreateSerializer
        if self.action in {"partial_update", "update"}:
            return ContentUpdateSerializer
        if self.action == "reject":
            return ContentRejectSerializer
        if self.action == "comments":
            return ContentCommentCreateSerializer
        return ContentSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def _error_response(self, *, message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            {"status": "error", "message": message, "errors": errors},
            status=status_code,
        )

    # ---------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------

    def list(self, request):
        try:
            user = resolve_request_user(request)
            role = getattr(getattr(user, "role", None), "name", None)

            status_filter = request.query_params.get("status")
            author_id = request.query_params.get("author_id")
            content_type = request.query_params.get("content_type")

            if status_filter == Content.Status.PENDING:
                if role == Role.SUPERVISOR:
                    qs = pending_content_for_moderator(user)
                elif role == Role.STUDENT:
                    qs = Content.objects.filter(author=user, status=Content.Status.PENDING, is_deleted=False)
                else:
                    qs = Content.objects.none()
            else:
                qs = self.get_queryset()

            if status_filter and status_filter != Content.Status.PENDING:
                qs = qs.filter(status=status_filter)
            if author_id:
                qs = qs.filter(author_id=author_id)
            if content_type:
                qs = qs.filter(content_type=content_type)

            return Response({"status": "success", "data": ContentSerializer(qs, many=True, context=self.get_serializer_context()).data})
        except Exception as exc:
            logger.exception("Community list failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, pk=None):
        user = resolve_request_user(request)
        try:
            content = self.get_object()
            self.check_object_permissions(request, content)
            return Response({"status": "success", "data": ContentSerializer(content, context=self.get_serializer_context()).data})
        except Http404:
            try:
                content = Content.objects.filter(author=user, is_deleted=False).get(pk=pk)
            except Content.DoesNotExist:
                return self._error_response(
                    message="Content not found.",
                    errors={"detail": "Not found."},
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            if content.author_id != user.id:
                return self._error_response(
                    message="You are not allowed to view this content.",
                    errors={"detail": "Forbidden."},
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            return Response({"status": "success", "data": ContentSerializer(content, context=self.get_serializer_context()).data})
        except drf_serializers.ValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Community retrieve failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request):
        try:
            user = resolve_request_user(request)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            content = create_content(author=user, data=serializer.validated_data)
            return Response({"status": "success", "data": ContentSerializer(content, context=self.get_serializer_context()).data}, status=status.HTTP_201_CREATED)
        except drf_serializers.ValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except DjangoValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except (DjangoPermissionDenied, DRFPermissionDenied) as exc:
            return self._error_response(
                message=str(exc),
                errors={"detail": str(exc)},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exc:
            logger.exception("Community create failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, pk=None):
        try:
            content = self.get_object()
            serializer = self.get_serializer(content, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            updated = update_content(user=request.user, content=content, data=serializer.validated_data)
            return Response({"status": "success", "data": ContentSerializer(updated, context=self.get_serializer_context()).data})
        except Http404:
            return self._error_response(
                message="Content not found.",
                errors={"detail": "Not found."},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except drf_serializers.ValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except DjangoValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except (DjangoPermissionDenied, DRFPermissionDenied) as exc:
            return self._error_response(
                message=str(exc),
                errors={"detail": str(exc)},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exc:
            logger.exception("Community update failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, pk=None):
        try:
            content = self.get_object()
            deleted = delete_content(user=request.user, content=content)
            return Response({"status": "success", "data": ContentSerializer(deleted, context=self.get_serializer_context()).data})
        except Http404:
            return self._error_response(
                message="Content not found.",
                errors={"detail": "Not found."},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except (DjangoPermissionDenied, DRFPermissionDenied) as exc:
            return self._error_response(
                message=str(exc),
                errors={"detail": str(exc)},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exc:
            logger.exception("Community delete failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ---------------------------------------------------------
    # Moderation
    # ---------------------------------------------------------

    @action(detail=False, methods=["get"])
    def pending(self, request):
        try:
            user = resolve_request_user(request)
            qs = pending_content_for_moderator(user)
            return Response({"status": "success", "data": ContentSerializer(qs, many=True, context=self.get_serializer_context()).data})
        except Exception as exc:
            logger.exception("Community pending failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        try:
            content = self.get_object()
            self.check_object_permissions(request, content)

            user = resolve_request_user(request)
            content = approve_content(moderator=user, content=content)
            return Response({"status": "success", "data": ContentSerializer(content, context=self.get_serializer_context()).data})
        except Http404:
            return self._error_response(
                message="Content not found.",
                errors={"detail": "Not found."},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except drf_serializers.ValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except DjangoValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except (DjangoPermissionDenied, DRFPermissionDenied) as exc:
            return self._error_response(
                message=str(exc),
                errors={"detail": str(exc)},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exc:
            logger.exception("Community approve failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
            return Response({"status": "success", "data": ContentSerializer(content, context=self.get_serializer_context()).data})
        except Http404:
            return self._error_response(
                message="Content not found.",
                errors={"detail": "Not found."},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except drf_serializers.ValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except DjangoValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except (DjangoPermissionDenied, DRFPermissionDenied) as exc:
            return self._error_response(
                message=str(exc),
                errors={"detail": str(exc)},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exc:
            logger.exception("Community reject failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        except Http404:
            return self._error_response(
                message="Content not found.",
                errors={"detail": "Not found."},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except drf_serializers.ValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except (DjangoPermissionDenied, DRFPermissionDenied) as exc:
            return self._error_response(
                message=str(exc),
                errors={"detail": str(exc)},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exc:
            logger.exception("Community like failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def react(self, request, pk=None):
        return self.like(request, pk=pk)

    @action(detail=True, methods=["post"], url_path="comments")
    def comments(self, request, pk=None):
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
        except Http404:
            return self._error_response(
                message="Content not found.",
                errors={"detail": "Not found."},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except drf_serializers.ValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=exc.detail,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except (DjangoPermissionDenied, DRFPermissionDenied) as exc:
            return self._error_response(
                message=str(exc),
                errors={"detail": str(exc)},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exc:
            logger.exception("Community comment failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ApprovalLogListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, CanViewApprovalLogs]
    serializer_class = CommunityApprovalLogSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)
        return approval_logs_for_user(user)


# ============================================================
# Student Public Rating API
# ============================================================

@extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["community"])
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
            {"status": "error", "message": "Unexpected error. See errors for details.", "errors": None},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
