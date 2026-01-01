# apps/evaluations/views.py
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User, Role
from medismile.utils.auth import resolve_request_user

from .models import Evaluation
from .serializers import (
    EvaluationSerializer,
    EvaluationCreateSerializer,
    EvaluationUpdateSerializer,
    PatientEvaluationCreateSerializer,
)
from .permissions import (
    CanViewEvaluation,
    CanCreateEvaluation,
    CanUpdateEvaluation,
    CanChangeEvaluationStatus,
)
from .selectors import evaluations_queryset_for_user, student_statistics
from .services import create_evaluation, update_evaluation, submit_evaluation, finalize_evaluation
from apps.notifications.services import notify_user


class EvaluationViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EvaluationSerializer

    def get_queryset(self):
        user = resolve_request_user(self.request)
        return evaluations_queryset_for_user(user)

    def list(self, request):
        qs = self.get_queryset()
        serializer = EvaluationSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        evaluation = self.get_object()
        self.check_object_permissions(request, evaluation)
        return Response(EvaluationSerializer(evaluation, context={"request": request}).data)

    def create(self, request):
        self.permission_classes = [IsAuthenticated, CanCreateEvaluation]
        self.check_permissions(request)

        ser = EvaluationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        actor = resolve_request_user(request)
        evaluation = create_evaluation(actor=actor, data=ser.validated_data)

        return Response(EvaluationSerializer(evaluation).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        evaluation = self.get_object()
        self.permission_classes = [IsAuthenticated, CanUpdateEvaluation]
        self.check_object_permissions(request, evaluation)

        ser = EvaluationUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)

        actor = resolve_request_user(request)
        evaluation = update_evaluation(actor=actor, evaluation=evaluation, data=ser.validated_data)

        return Response(EvaluationSerializer(evaluation).data, status=status.HTTP_200_OK)

    def get_object(self):
        obj = super().get_object()
        # Enforce object view permission
        self.permission_classes = [IsAuthenticated, CanViewEvaluation]
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        evaluation = self.get_object()
        self.permission_classes = [IsAuthenticated, CanChangeEvaluationStatus]
        self.check_object_permissions(request, evaluation)

        actor = resolve_request_user(request)
        evaluation = submit_evaluation(actor=actor, evaluation=evaluation)
        return Response(EvaluationSerializer(evaluation).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        evaluation = self.get_object()
        self.permission_classes = [IsAuthenticated, CanChangeEvaluationStatus]
        self.check_object_permissions(request, evaluation)

        actor = resolve_request_user(request)
        evaluation = finalize_evaluation(actor=actor, evaluation=evaluation)
        return Response(EvaluationSerializer(evaluation).data, status=status.HTTP_200_OK)


# ------------------------------------------------------------
# Patient feedback about student/doctor
# ------------------------------------------------------------
class PatientEvaluationCreateView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        actor = resolve_request_user(request)
        if getattr(getattr(actor, "role", None), "name", None) != Role.PATIENT:
            return Response({"detail": "Only patients can submit this evaluation."}, status=status.HTTP_403_FORBIDDEN)

        ser = PatientEvaluationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        evaluation = create_evaluation(actor=actor, data=data)

        # Notify student (doctor) and optionally supervisor if case/supervisor linked
        notify_user(
            recipient=data["student"],
            notification_type="evaluation_submitted",
            title="تم تقديم تقييم من المريض",
            message=f"تقييم جديد بدرجة {data['score']}",
            target_object=evaluation,
            payload={"evaluation_id": str(evaluation.id), "score": data["score"]},
        )

        return Response(EvaluationSerializer(evaluation).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_evaluation_statistics(request, student_id):
    user = resolve_request_user(request)

    try:
        student = User.objects.get(id=student_id, role__name=Role.STUDENT)
    except User.DoesNotExist:
        return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

    # Authorization (same rules)
    if getattr(getattr(user, "role", None), "name", None) == Role.STUDENT and user.id != student.id:
        return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

    if getattr(getattr(user, "role", None), "name", None) in {Role.SUPERVISOR, Role.UNIVERSITY_ADMIN}:
        if student.university_id not in {getattr(user, "university_id", None)}:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)

    return Response(student_statistics(student), status=status.HTTP_200_OK)
