# apps/evaluations/views.py

from django.db.models import Avg
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Evaluation, EvaluationStatus
from .serializers import (
    EvaluationSerializer,
    EvaluationCreateSerializer,
    EvaluationUpdateSerializer,
    EvaluationActionSerializer,
)

from apps.accounts.models import User


class EvaluationViewSet(viewsets.ModelViewSet):
    """
    Evaluation API:
    - Student: read own evaluations
    - Supervisor: create / read evaluations within university
    - University Admin: full read + finalize
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Evaluation.objects.select_related(
            "university",
            "evaluator",
            "student",
            "case",
            "session",
            "appointment",
        )

        if user.role == "student":
            return queryset.filter(student=user)

        if user.role in ["supervisor", "university_admin"]:
            return queryset.filter(university=user.university)

        return queryset.none()

    def get_serializer_class(self):
        if self.action == "create":
            return EvaluationCreateSerializer
        if self.action in ["update", "partial_update"]:
            return EvaluationUpdateSerializer
        return EvaluationSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if user.role not in ["supervisor", "university_admin"]:
            raise PermissionError(_("Only supervisors or university admins can create evaluations."))
        serializer.save()

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        evaluation = self.get_object()
        serializer = EvaluationActionSerializer(
            data={"action": "submit"},
            context={"evaluation": evaluation, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            EvaluationSerializer(evaluation, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        evaluation = self.get_object()
        serializer = EvaluationActionSerializer(
            data={"action": "finalize"},
            context={"evaluation": evaluation, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            EvaluationSerializer(evaluation, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_evaluation_statistics(request, student_id):
    """
    Get evaluation statistics for a student.
    Accessible by:
    - Student (self)
    - Supervisor / University Admin (same university)
    """

    user = request.user

    try:
        student = User.objects.get(id=student_id, role="student")
    except User.DoesNotExist:
        return Response(
            {"detail": _("Student not found.")},
            status=status.HTTP_404_NOT_FOUND,
        )

    if user.role == "student" and user != student:
        return Response({"detail": _("Not allowed.")}, status=status.HTTP_403_FORBIDDEN)

    if user.role in ["supervisor", "university_admin"]:
        if student.university_id != user.university_id:
            return Response({"detail": _("Not allowed.")}, status=status.HTTP_403_FORBIDDEN)

    evaluations = Evaluation.objects.filter(student=student)

    if not evaluations.exists():
        return Response(
            {
                "student_id": str(student.id),
                "average_score": None,
                "total_evaluations": 0,
            },
            status=status.HTTP_200_OK,
        )

    average_score = evaluations.aggregate(avg=Avg("score"))["avg"]

    return Response(
        {
            "student_id": str(student.id),
            "student_name": student.get_full_name() or student.username,
            "average_score": round(average_score, 2) if average_score else None,
            "total_evaluations": evaluations.count(),
            "by_status": {
                status_key: evaluations.filter(status=status_key).count()
                for status_key, _ in EvaluationStatus.choices
            },
        },
        status=status.HTTP_200_OK,
    )
