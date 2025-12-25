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

from apps.ai.services.ai_client import (
    analyze_symptoms,
    analyze_dental_images,
    fuse_ai_results,
)
from apps.ai.services.decision_policy import build_final_diagnosis

from apps.accounts.permissions import IsPatient
from apps.cases.models import Case


# ============================================================
# LIST AI DIAGNOSES
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
# RETRIEVE SINGLE AI DIAGNOSIS
# ============================================================

class AIDiagnosisDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single AI diagnosis report.
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
# CREATE AI DIAGNOSIS (PATIENT ONLY)
# ============================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsPatient])
def create_ai_diagnosis(request):
    """
    Run a full AI diagnosis workflow for a patient.

    Workflow:
    1. Validate request & case ownership
    2. Run NLP analysis (AraBERT)
    3. Run Vision analysis (YOLO) [optional]
    4. Run Fusion model (BART)
    5. Apply decision policy
    6. Persist unified AI diagnosis
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
    # Optional Images (from request.FILES)
    # --------------------------------------------------------
    image_files = request.FILES.getlist("images")

    # --------------------------------------------------------
    # Step 1: NLP Analysis (AraBERT)
    # --------------------------------------------------------
    symptom_result = analyze_symptoms(symptoms_text)

    # --------------------------------------------------------
    # Step 2: Vision Analysis (YOLO) [Optional]
    # --------------------------------------------------------
    image_result = analyze_dental_images(image_files)

    # --------------------------------------------------------
    # Step 3: Fusion Model (BART)
    # --------------------------------------------------------
    fusion_result = fuse_ai_results(
        symptom_result=symptom_result,
        image_result=image_result,
    )

    # --------------------------------------------------------
    # Step 4: Decision Policy (Final Diagnosis)
    # --------------------------------------------------------
    final_result = build_final_diagnosis(
        symptom_analysis=symptom_result,
        image_analysis=image_result,
        fusion_result=fusion_result,
    )

    # --------------------------------------------------------
    # Step 5: Persist AI Diagnosis
    # --------------------------------------------------------
    ai_diagnosis = AIDiagnosis.objects.create(
        case=case,
        patient=request.user,
        requested_by=request.user,

        # Input
        raw_symptoms=symptoms_text,
        normalized_symptoms=symptom_result.get("metadata", {}).get("normalized_text"),

        # Headline & findings
        diagnosis_label=fusion_result.get("primary_diagnosis"),
        primary_diagnosis=final_result.get("primary_diagnosis"),
        detected_findings=final_result.get("detected_findings"),

        # Report
        patient_explanation=final_result.get("patient_explanation"),
        report_text=final_result.get("patient_explanation"),

        # Risk & confidence
        confidence_level=final_result.get("confidence_level"),
        severity_level=final_result.get("severity_level"),
        urgency_level=final_result.get("urgency_level"),

        # Guidance
        recommendations=final_result.get("recommendations"),

        # Metadata
        ai_metadata=final_result.get("ai_metadata"),

        status=DiagnosisStatus.COMPLETED,
        created_at=timezone.now(),
    )

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------
    return Response(
        {
            "message": _("AI diagnosis generated successfully."),
            "diagnosis": AIDiagnosisSerializer(ai_diagnosis).data,
        },
        status=status.HTTP_201_CREATED,
    )
