# apps/evaluations/views.py
import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers as drf_serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Role, User
from medismile.utils.auth import resolve_request_user

from .permissions import (
    CanAdjustEvaluation,
    CanCreateEvaluation,
    CanFinalizeEvaluation,
    CanViewEvaluation,
)
from .selectors import evaluations_queryset_for_user, student_rating
from .serializers import (
    EvaluationAdjustSerializer,
    EvaluationCreateSerializer,
    EvaluationRatingSerializer,
    EvaluationSerializer,
)
from .services import adjust_evaluation, create_evaluation, finalize_evaluation

logger = logging.getLogger(__name__)


def _get_user_university_ids(user) -> set:
    ids = set()
    for attr in (
        "studentprofile_profile",
        "supervisorprofile_profile",
        "universityadminprofile_profile",
        "patientprofile_profile",
    ):
        try:
            profile = getattr(user, attr, None)
        except Exception:
            profile = None
        uni_id = getattr(profile, "university_id", None)
        if uni_id:
            ids.add(uni_id)
    rel = getattr(user, "universities", None)
    if rel is not None and hasattr(rel, "all"):
        ids |= set(rel.values_list("id", flat=True))
    return ids


class EvaluationViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EvaluationSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)
        return evaluations_queryset_for_user(user)

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), CanCreateEvaluation()]
        if self.action == "adjust":
            return [IsAuthenticated(), CanAdjustEvaluation()]
        if self.action == "finalize":
            return [IsAuthenticated(), CanFinalizeEvaluation()]
        if self.action == "retrieve":
            return [IsAuthenticated(), CanViewEvaluation()]
        return [IsAuthenticated()]

    def _error_response(self, *, message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            {"status": "error", "message": message, "errors": errors},
            status=status_code,
        )

    def list(self, request):
        try:
            qs = self.get_queryset()

            status_filter = request.query_params.get("status")
            target_type = request.query_params.get("target_type")
            evaluator_role = request.query_params.get("evaluator_role")
            student_id = request.query_params.get("student_id")
            target_id = request.query_params.get("target_id")

            if status_filter:
                qs = qs.filter(status=status_filter)
            if target_type:
                qs = qs.filter(target_type=target_type)
            if evaluator_role:
                qs = qs.filter(evaluator_role=evaluator_role)
            if student_id:
                qs = qs.filter(student_id=student_id)
            if target_id:
                qs = qs.filter(target_id=target_id)

            return Response({"status": "success", "data": EvaluationSerializer(qs, many=True).data})
        except Exception as exc:
            logger.exception("Evaluations list failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, pk=None):
        try:
            evaluation = self.get_object()
            self.check_object_permissions(request, evaluation)
            return Response({"status": "success", "data": EvaluationSerializer(evaluation).data})
        except Http404:
            return self._error_response(
                message="Evaluation not found.",
                errors={"detail": "Not found."},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except drf_serializers.ValidationError as exc:
            return self._error_response(message="Invalid request.", errors=exc.detail)
        except DjangoValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc),
            )
        except Exception as exc:
            logger.exception("Evaluations retrieve failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request):
        try:
            serializer = EvaluationCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            actor = resolve_request_user(request)
            evaluation = create_evaluation(actor=actor, data=serializer.validated_data)

            return Response(
                {"status": "success", "data": EvaluationSerializer(evaluation).data},
                status=status.HTTP_201_CREATED,
            )
        except drf_serializers.ValidationError as exc:
            return self._error_response(message="Invalid request.", errors=exc.detail)
        except DjangoValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc),
            )
        except (DjangoPermissionDenied,) as exc:
            return self._error_response(
                message=str(exc),
                errors={"detail": str(exc)},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exc:
            logger.exception("Evaluations create failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["patch"])
    def adjust(self, request, pk=None):
        try:
            evaluation = self.get_object()
            self.check_object_permissions(request, evaluation)

            serializer = EvaluationAdjustSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            actor = resolve_request_user(request)
            evaluation = adjust_evaluation(
                actor=actor,
                evaluation=evaluation,
                new_score=serializer.validated_data["new_score"],
                reason=serializer.validated_data["reason"],
            )

            return Response({"status": "success", "data": EvaluationSerializer(evaluation).data})
        except Http404:
            return self._error_response(
                message="Evaluation not found.",
                errors={"detail": "Not found."},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except drf_serializers.ValidationError as exc:
            return self._error_response(message="Invalid request.", errors=exc.detail)
        except DjangoValidationError as exc:
            return self._error_response(
                message="Invalid request.",
                errors=getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc),
            )
        except DjangoPermissionDenied as exc:
            return self._error_response(
                message=str(exc),
                errors={"detail": str(exc)},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exc:
            logger.exception("Evaluations adjust failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        try:
            evaluation = self.get_object()
            self.check_object_permissions(request, evaluation)

            actor = resolve_request_user(request)
            evaluation = finalize_evaluation(actor=actor, evaluation=evaluation)

            return Response({"status": "success", "data": EvaluationSerializer(evaluation).data})
        except Http404:
            return self._error_response(
                message="Evaluation not found.",
                errors={"detail": "Not found."},
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except DjangoPermissionDenied as exc:
            return self._error_response(
                message=str(exc),
                errors={"detail": str(exc)},
                status_code=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exc:
            logger.exception("Evaluations finalize failed", exc_info=exc)
            return self._error_response(
                message="Unexpected error. See errors for details.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["evaluations"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_rating_view(request, student_id):
    try:
        student = User.objects.get(id=student_id, role__name=Role.STUDENT)
    except User.DoesNotExist:
        return Response(
            {"status": "error", "message": "Student not found.", "errors": {"detail": "Not found."}},
            status=status.HTTP_404_NOT_FOUND,
        )

    user = resolve_request_user(request)
    role_name = getattr(getattr(user, "role", None), "name", None)
    student_university_id = getattr(getattr(student, "studentprofile_profile", None), "university_id", None)

    if role_name == Role.STUDENT and user.id != student.id:
        return Response(
            {"status": "error", "message": "Not allowed.", "errors": {"detail": "Forbidden."}},
            status=status.HTTP_403_FORBIDDEN,
        )

    if role_name in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
        if student_university_id not in _get_user_university_ids(user):
            return Response(
                {"status": "error", "message": "Not allowed.", "errors": {"detail": "Forbidden."}},
                status=status.HTTP_403_FORBIDDEN,
            )

    if role_name == Role.PATIENT:
        patient_university_id = getattr(getattr(user, "patientprofile_profile", None), "university_id", None)
        if patient_university_id and student_university_id and patient_university_id != student_university_id:
            return Response(
                {"status": "error", "message": "Not allowed.", "errors": {"detail": "Forbidden."}},
                status=status.HTTP_403_FORBIDDEN,
            )

    if role_name == Role.TECH_SUPPORT:
        return Response(
            {"status": "error", "message": "Not allowed.", "errors": {"detail": "Forbidden."}},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        data = student_rating(student)
        return Response({"status": "success", "data": EvaluationRatingSerializer(data).data})
    except Exception as exc:
        logger.exception("Student rating failed", exc_info=exc)
        return Response(
            {"status": "error", "message": "Unexpected error. See errors for details.", "errors": None},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
