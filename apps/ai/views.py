# apps/ai/views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.cases.models import Case

from .models import AIDiagnosis, DiagnosisStatus
from .serializers import (
    AIDiagnosisSerializer,
    AIDiagnosisRequestSerializer,
    AIDiagnosisReviewSerializer,
)
from .selectors import get_ai_diagnosis_queryset_for_user
from .permissions import CanRequestAIDiagnosis, CanAccessAIDiagnosis, CanReviewAIDiagnosis, CanViewAIHealth
from .services import request_ai_diagnosis, review_ai_diagnosis
from .integrations.endpoints import get_ai_engines_config


class AIDiagnosisListView(generics.ListAPIView):
    serializer_class = AIDiagnosisSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_ai_diagnosis_queryset_for_user(user=self.request.user)


class AIDiagnosisDetailView(generics.RetrieveAPIView):
    serializer_class = AIDiagnosisSerializer
    permission_classes = [IsAuthenticated, CanAccessAIDiagnosis]

    def get_queryset(self):
        return get_ai_diagnosis_queryset_for_user(user=self.request.user)


@api_view(["POST"])
@permission_classes([IsAuthenticated, CanRequestAIDiagnosis])
@throttle_classes([ScopedRateThrottle])
def create_ai_diagnosis(request):
    serializer = AIDiagnosisRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    diagnosis = request_ai_diagnosis(
        actor=request.user,
        case_id=serializer.validated_data["case_id"],
        symptoms_text=serializer.validated_data["symptoms_text"],
        image_urls=serializer.validated_data.get("image_urls") or [],
    )

    return Response(
        {"diagnosis": AIDiagnosisSerializer(diagnosis).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, CanReviewAIDiagnosis])
@throttle_classes([ScopedRateThrottle])
def review_ai_diagnosis_view(request, pk):
    diagnosis = get_ai_diagnosis_queryset_for_user(user=request.user).get(pk=pk)
    # object-level permission check
    self_perm = CanReviewAIDiagnosis()
    if not self_perm.has_object_permission(request, None, diagnosis):
        return Response(status=status.HTTP_403_FORBIDDEN)

    serializer = AIDiagnosisReviewSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    reviewed = review_ai_diagnosis(
        actor=request.user,
        diagnosis_id=str(diagnosis.id),
        approved=serializer.validated_data.get("approved", True),
        note=serializer.validated_data.get("note"),
    )

    return Response(
        {"diagnosis": AIDiagnosisSerializer(reviewed).data},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, CanViewAIHealth])
@throttle_classes([ScopedRateThrottle])
def ai_health_view(request):
    configs = get_ai_engines_config()
    engines = {
        "symptoms": {"url": configs.symptoms.base_url, "timeout": configs.symptoms.timeout_seconds},
        "vision": {"url": configs.vision.base_url, "timeout": configs.vision.timeout_seconds},
        "fusion": {"url": configs.fusion.base_url, "timeout": configs.fusion.timeout_seconds},
    }
    return Response({"engines": engines}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated, CanRequestAIDiagnosis])
@throttle_classes([ScopedRateThrottle])
def my_ai_analysis(request):
    """
    Patient-only endpoint to fetch the latest AI analysis without providing a case_id.
    """
    patient = request.user
    case = Case.objects.filter(patient=patient).order_by("-created_at").first()
    if not case:
        return Response({"detail": "لا توجد حالة مسجلة حاليًا."}, status=status.HTTP_404_NOT_FOUND)

    diagnosis = (
        AIDiagnosis.objects.filter(case=case, patient=patient)
        .order_by("-created_at")
        .first()
    )

    if not diagnosis or diagnosis.status not in {DiagnosisStatus.COMPLETED, DiagnosisStatus.REVIEWED}:
        return Response(
            {"status": "processing", "message": "يتم الآن تحليل حالتك، يرجى الانتظار قليلاً."},
            status=status.HTTP_202_ACCEPTED,
        )

    suspected_condition = diagnosis.primary_diagnosis or diagnosis.diagnosis_label
    response_data = {
        "case_id": str(case.id),
        "status": "analyzed",
        "ai_summary": {
            "suspected_condition": suspected_condition,
            "severity": diagnosis.severity_level,
            "confidence_level": diagnosis.confidence_level,
            "urgency_level": diagnosis.urgency_level,
        },
        "patient_report": {
            "summary": diagnosis.patient_explanation or "",
            "recommendation": diagnosis.recommendations or "",
            "note": "هذا التقرير مبني على تحليل آلي مبدئي ولا يغني عن التشخيص الطبي.",
        },
        "last_updated": diagnosis.updated_at.isoformat(),
    }

    return Response(response_data, status=status.HTTP_200_OK)


# DRF throttle scopes for function-based views
create_ai_diagnosis.throttle_scope = "ai-diagnose"
review_ai_diagnosis_view.throttle_scope = "ai-review"
ai_health_view.throttle_scope = "ai-health"
my_ai_analysis.throttle_scope = "ai-my-analysis"
