# apps/ai/views.py

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AIDiagnosis, DiagnosisStatus
from .serializers import (
    AIDiagnosisSerializer,
    AIDiagnosisRequestSerializer,
)
# from apps.ai.services import 
from apps.ai.services.ai_client import analyze_symptoms_via_ai_engine

from apps.accounts.permissions import IsPatient
from apps.cases.models import Case


# ============================================================
# List AI Diagnoses
# ============================================================

class AIDiagnosisListView(generics.ListAPIView):
    """
    List AI diagnoses based on user role and case relationship.
    """

    serializer_class = AIDiagnosisSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = user.role.name

        queryset = AIDiagnosis.objects.select_related(
            "case",
            "patient",
            "requested_by",
            "reviewed_by",
        )

        if role == "patient":
            return queryset.filter(patient=user)

        if role == "student":
            case_ids = Case.objects.filter(student=user).values_list("id", flat=True)
            return queryset.filter(case_id__in=case_ids)

        if role == "supervisor":
            case_ids = Case.objects.filter(supervisor=user).values_list("id", flat=True)
            return queryset.filter(case_id__in=case_ids)

        if role in ("university_admin", "tech_support"):
            return queryset

        return queryset.none()


# ============================================================
# Retrieve AI Diagnosis
# ============================================================

class AIDiagnosisDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single AI diagnosis.
    """

    queryset = AIDiagnosis.objects.select_related(
        "case",
        "patient",
        "requested_by",
        "reviewed_by",
    )
    serializer_class = AIDiagnosisSerializer
    permission_classes = [IsAuthenticated]


# ============================================================
# Analyze Symptoms (Patient Only)
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsPatient])
def analyze_symptoms(request):
    """
    Run AI symptom-based diagnosis for a patient.
    """

    serializer = AIDiagnosisRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    case_id = serializer.validated_data["case_id"]
    symptoms_text = serializer.validated_data["symptoms_text"]

    # --------------------------------------------------------
    # Validate Case Ownership
    # --------------------------------------------------------
    case = get_object_or_404(
        Case,
        id=case_id,
        patient=request.user,
    )

    # --------------------------------------------------------
    # Run AI Service (Pure Orchestration)
    # --------------------------------------------------------
    ai_result = analyze_symptoms_via_ai_engine(symptoms_text)



    # --------------------------------------------------------
    # Persist AI Diagnosis
    # --------------------------------------------------------
    ai_diagnosis = AIDiagnosis.objects.create(
        case=case,
        patient=request.user,
        requested_by=request.user,
        raw_symptoms=symptoms_text,
        normalized_symptoms=ai_result.metadata.get("normalized_text"),
        diagnosis_label=ai_result.diagnosis_label,
        confidence_level=ai_result.confidence_level,
        severity_level=ai_result.severity_level,
        urgency_level=ai_result.urgency_level,
        patient_explanation=ai_result.patient_explanation,
        recommendations=ai_result.recommendations,
        ai_metadata=ai_result.metadata,
        status=DiagnosisStatus.COMPLETED,
        created_at=timezone.now(),
    )

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------
    return Response(
        {
            "message": _("AI analysis completed successfully."),
            "diagnosis": AIDiagnosisSerializer(ai_diagnosis).data,
        },
        status=status.HTTP_201_CREATED,
    )
