# apps/ai/views.py
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.cases.models import Case
from medismile.openapi import (
    BINARY_IMAGE,
    AIEnginesHealth,
    DetailMessage,
    ErrorEnvelope,
    MyAnalysisResponse,
    ProcessingResponse,
)

from .models import AIDiagnosis, AIImageUpload, DiagnosisStatus
from .serializers import (
    MAX_IMAGES_PER_DIAGNOSIS,
    AIDiagnoseMultipartSerializer,
    AIDiagnoseResponseSerializer,
    AIDiagnosisSerializer,
    AIDiagnosisRequestSerializer,
    AIDiagnosisReviewSerializer,
    AIImageUploadCreateSerializer,
    AIImageUploadSerializer,
)
from .selectors import get_ai_diagnosis_queryset_for_user
from .permissions import CanRequestAIDiagnosis, CanAccessAIDiagnosis, CanReviewAIDiagnosis, CanViewAIHealth
from .services import create_ai_image_upload, request_ai_diagnosis, review_ai_diagnosis
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


# Multipart field names accepted for direct image upload on /diagnose/.
_IMAGE_FILE_FIELDS = ("image", "images", "image_file")


class AIImageUploadView(APIView):
    """
    POST /api/ai/images/ — patient uploads one dental photo (multipart field
    ``image``). Returns the stored image id to pass as ``image_ids`` to
    /api/ai/diagnose/. The file is validated, EXIF-stripped and re-encoded.
    """

    permission_classes = [IsAuthenticated, CanRequestAIDiagnosis]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai-image-upload"

    @extend_schema(
        request={"multipart/form-data": AIImageUploadCreateSerializer},
        responses={201: AIImageUploadSerializer, 400: ErrorEnvelope, 403: ErrorEnvelope},
        tags=["ai"],
    )
    def post(self, request):
        serializer = AIImageUploadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = create_ai_image_upload(actor=request.user, uploaded_file=serializer.validated_data["image"])
        return Response(
            AIImageUploadSerializer(upload, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AIImageFileView(APIView):
    """
    GET /api/ai/images/<id>/file/ — authenticated download of an uploaded
    image. Visible to the owning patient, and to staff who can see the
    diagnosis it was attached to (same scoping as the diagnosis itself).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: BINARY_IMAGE, 404: ErrorEnvelope}, tags=["ai"])
    def get(self, request, pk):
        upload = get_object_or_404(AIImageUpload.objects.select_related("diagnosis"), pk=pk)
        allowed = upload.patient_id == request.user.id or (
            upload.diagnosis_id
            and get_ai_diagnosis_queryset_for_user(user=request.user).filter(pk=upload.diagnosis_id).exists()
        )
        if not allowed:
            raise Http404
        response = FileResponse(upload.image.open("rb"), content_type=upload.content_type)
        response["Cache-Control"] = "private, max-age=300"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class AIDiagnoseView(APIView):
    """
    POST /api/ai/diagnose/ — run the text + image AI pipeline for the patient.

    Accepts JSON (``symptoms_text`` + optional ``image_ids``) or multipart
    (``symptoms_text`` + image file under ``image``/``images``/``image_file``).
    Returns 201 on success and 503 (with the FAILED diagnosis) when every AI
    engine is unavailable.
    """

    permission_classes = [IsAuthenticated, CanRequestAIDiagnosis]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai-diagnose"

    @extend_schema(
        request={
            "application/json": AIDiagnosisRequestSerializer,
            "multipart/form-data": AIDiagnoseMultipartSerializer,
        },
        responses={
            201: AIDiagnoseResponseSerializer,
            400: ErrorEnvelope,
            403: ErrorEnvelope,
            503: OpenApiResponse(
                AIDiagnoseResponseSerializer,
                description="Every AI engine failed; `diagnosis.status` is `failed` and `detail` holds a user-facing message.",
            ),
        },
        tags=["ai"],
    )
    def post(self, request):
        files = []
        for field in _IMAGE_FILE_FIELDS:
            files.extend(request.FILES.getlist(field))
        if len(files) > MAX_IMAGES_PER_DIAGNOSIS:
            raise ValidationError({"images": f"At most {MAX_IMAGES_PER_DIAGNOSIS} images per diagnosis."})

        data = request.data
        if hasattr(data, "getlist"):
            # Multipart/form: lists arrive as repeated keys.
            data = {
                "symptoms_text": data.get("symptoms_text"),
                "patient_id": data.get("patient_id") or None,
                "image_ids": data.getlist("image_ids"),
                "image_urls": data.getlist("image_urls"),
            }
        serializer = AIDiagnosisRequestSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        diagnosis, suggestions = request_ai_diagnosis(
            actor=request.user,
            symptoms_text=serializer.validated_data["symptoms_text"],
            patient_id=serializer.validated_data.get("patient_id"),
            image_urls=serializer.validated_data.get("image_urls") or [],
            image_ids=serializer.validated_data.get("image_ids") or [],
            uploaded_files=files,
        )

        body = {
            "diagnosis": AIDiagnosisSerializer(diagnosis, context={"request": request}).data,
            "primary_suggestion": suggestions.get("primary_suggestion"),
            "next_suggestion": suggestions.get("next_suggestion"),
            "all_suggestions": suggestions.get("all_suggestions"),
        }
        if diagnosis.status == DiagnosisStatus.FAILED:
            body["detail"] = diagnosis.error_message
            return Response(body, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(body, status=status.HTTP_201_CREATED)


@extend_schema(
    request=AIDiagnosisReviewSerializer,
    responses={200: inline_serializer("AIDiagnosisReviewResponse", {"diagnosis": AIDiagnosisSerializer()})},
    tags=["ai"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated, CanReviewAIDiagnosis])
@throttle_classes([ScopedRateThrottle])
def review_ai_diagnosis_view(request, pk):
    diagnosis = get_object_or_404(get_ai_diagnosis_queryset_for_user(user=request.user), pk=pk)
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
        {"diagnosis": AIDiagnosisSerializer(reviewed, context={"request": request}).data},
        status=status.HTTP_200_OK,
    )


@extend_schema(responses={200: AIEnginesHealth}, tags=["ai"])
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


@extend_schema(
    responses={200: MyAnalysisResponse, 202: ProcessingResponse, 404: DetailMessage},
    tags=["ai"],
)
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


# DRF throttle scopes for function-based views. ScopedRateThrottle reads the
# scope from the *view class* that @api_view generates (exposed as ``.cls``);
# setting it on the returned function alone is silently ignored.
review_ai_diagnosis_view.cls.throttle_scope = "ai-review"
ai_health_view.cls.throttle_scope = "ai-health"
my_ai_analysis.cls.throttle_scope = "ai-my-analysis"
