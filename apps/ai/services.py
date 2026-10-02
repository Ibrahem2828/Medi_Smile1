# apps/ai/services.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import Role
from apps.audit.services import log_audit_event
from apps.cases.models import Case

from .constants import (
    build_ai_metadata,
    normalize_confidence,
    normalize_diagnosis_label,
    normalize_severity,
    normalize_urgency,
)
from .images import sanitize_image
from .models import (
    AIDiagnosis,
    AIImageUpload,
    ConfidenceLevel,
    DiagnosisStatus,
    SeverityLevel,
    UrgencyLevel,
)
from .integrations.endpoints import get_ai_engines_config
from .integrations.engine import AIEngineError, AIEnginesConfig, ImageInput, analyze_case


def _get_engine_config() -> AIEnginesConfig:
    """
    Returns configuration for the three AI engines (symptoms, vision, fusion).
    Resolved centrally in integrations.endpoints.
    """
    return get_ai_engines_config()


def _extract_suggestions(engine_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract ordered suggestions from fusion output to drive patient-facing flow.
    """
    suggestions = []
    # prefer explicit fusion outputs
    if isinstance(engine_payload, dict):
        if isinstance(engine_payload.get("fusion_results"), list):
            suggestions = engine_payload.get("fusion_results") or []
        elif isinstance(engine_payload.get("suspected_conditions"), list):
            suggestions = engine_payload.get("suspected_conditions") or []

    # ensure list of dicts with severity/urgency keys
    normalized = []
    for item in suggestions:
        if not isinstance(item, dict):
            continue
        normalized.append(item)

    # Primary/next logic
    high_items = [i for i in normalized if str(i.get("severity_level", "")).lower() == "high" or str(i.get("urgency", "")).lower() == "urgent"]
    primary = high_items[0] if high_items else (normalized[0] if normalized else None)
    next_item = high_items[1] if len(high_items) > 1 else None

    return {
        "all_suggestions": normalized,
        "primary_suggestion": primary,
        "next_suggestion": next_item,
    }


def _build_ai_audit_hook(*, actor, case):
    def _hook(action: str, metadata: Dict[str, Any]) -> None:
        metadata = dict(metadata or {})
        metadata.setdefault("case_id", str(getattr(case, "id", "")))
        log_audit_event(
            user=actor,
            university=getattr(case, "university", None),
            action=action,
            description="AI engine call",
            content_object=case,
            metadata=metadata,
        )

    return _hook


def _require_patient(actor) -> None:
    role = getattr(getattr(actor, "role", None), "name", None)
    if role != Role.PATIENT:
        raise PermissionDenied("Only patients can request AI diagnosis.")


def create_ai_image_upload(*, actor, uploaded_file) -> AIImageUpload:
    """
    Patient-only: validate, sanitise and store one dental photo for later
    analysis. Returns the stored record (referenced by id from diagnose).
    """
    _require_patient(actor)
    clean = sanitize_image(uploaded_file)

    upload = AIImageUpload(
        patient=actor,
        content_type=clean.content_type,
        size_bytes=len(clean.content),
        width=clean.width,
        height=clean.height,
        sha256=clean.sha256,
    )
    upload.image.save(f"upload.{clean.extension}", ContentFile(clean.content), save=False)
    upload.save()

    log_audit_event(
        user=actor,
        university=None,
        action="ai.image.uploaded",
        description="Patient uploaded an image for AI analysis",
        content_object=upload,
        metadata={"size_bytes": upload.size_bytes, "content_type": upload.content_type},
    )
    return upload


def _resolve_uploads(*, actor, image_ids) -> List[AIImageUpload]:
    """Load the patient's own, not-yet-used uploads in the requested order."""
    if not image_ids:
        return []
    wanted = [str(i) for i in image_ids]
    found = {
        str(u.id): u
        for u in AIImageUpload.objects.select_for_update().filter(
            id__in=wanted, patient=actor, diagnosis__isnull=True
        )
    }
    missing = [i for i in wanted if i not in found]
    if missing:
        raise ValidationError({"image_ids": "Unknown or already used image id(s): " + ", ".join(missing)})
    return [found[i] for i in wanted]


def _to_image_inputs(uploads: List[AIImageUpload]) -> List[ImageInput]:
    inputs: List[ImageInput] = []
    for upload in uploads:
        with upload.image.open("rb") as fh:
            content = fh.read()
        inputs.append(
            ImageInput(
                filename=f"{upload.id}.{upload.image.name.rsplit('.', 1)[-1]}",
                content=content,
                content_type=upload.content_type,
                source_url=f"ai-upload:{upload.id}",
            )
        )
    return inputs


def request_ai_diagnosis(
    *,
    actor,
    case_id=None,
    patient_id=None,
    symptoms_text: str,
    image_urls: Optional[List[str]] = None,
    image_ids: Optional[List[Any]] = None,
    uploaded_files: Optional[List[Any]] = None,
) -> tuple[AIDiagnosis, Dict[str, Any]]:
    """
    Patient-only: create AIDiagnosis by calling the external AI engines.
    Also logs audit for request/result/failure.

    Always returns ``(diagnosis, suggestions)``. When every engine fails the
    diagnosis is persisted with status FAILED and ``suggestions`` is empty —
    callers must check ``diagnosis.status``.

    The engine calls (up to ~3 × AI_ENGINE_TIMEOUT) deliberately run *outside*
    any database transaction so no row locks or connections are held while
    waiting on the network, and so the FAILED record is never rolled back.
    """
    _require_patient(actor)

    if patient_id and str(patient_id) != str(getattr(actor, "id", None)):
        raise PermissionDenied("Patient ID does not match the authenticated user.")

    # Validate/store any direct uploads first so bad files fail fast (400).
    direct_uploads = [create_ai_image_upload(actor=actor, uploaded_file=f) for f in (uploaded_files or [])]

    with transaction.atomic():
        # Lock claimed uploads before associating them. Two simultaneous
        # requests cannot both consume the same image id.
        uploads = direct_uploads + _resolve_uploads(actor=actor, image_ids=image_ids)
        case = None
        if case_id:
            case = Case.objects.select_related("university").get(id=case_id, patient=actor)
        else:
            case = (
                Case.objects.select_related("university")
                .filter(patient=actor, status__in=Case.ACTIVE_STATUSES)
                .order_by("-created_at")
                .first()
            )
            if not case:
                # Auto-create a lightweight case for this AI request
                title = f"AI Analysis - {symptoms_text[:50]}"
                case = Case.objects.create(
                    patient=actor,
                    title=title,
                    description=symptoms_text,
                )

        # Create a PENDING record first (auditable even if engine fails)
        diagnosis = AIDiagnosis.objects.create(
            case=case,
            patient=actor,
            requested_by=actor,
            raw_symptoms=symptoms_text,
            status=DiagnosisStatus.PENDING,
        )
        if uploads:
            claimed = AIImageUpload.objects.filter(
                id__in=[u.id for u in uploads], patient=actor, diagnosis__isnull=True
            ).update(diagnosis=diagnosis)
            if claimed != len(uploads):
                raise ValidationError({"image_ids": "One or more images were already claimed by another request."})

        log_audit_event(
            user=actor,
            university=getattr(case, "university", None),
            action="ai.diagnosis.requested",
            description="Patient requested AI diagnosis",
            content_object=diagnosis,
            metadata={"case_id": str(case.id), "images_count": len(uploads) or len(image_urls or [])},
        )

    try:
        engine_payload: Dict[str, Any] = analyze_case(
            configs=_get_engine_config(),
            symptoms_text=symptoms_text,
            image_urls=[] if uploads else (image_urls or []),
            images=_to_image_inputs(uploads),
            case_id=str(case.id),
            audit_hook=_build_ai_audit_hook(actor=actor, case=case),
        )
    except AIEngineError as exc:
        raw_error = str(exc)
        friendly_error = "خدمة الذكاء الاصطناعي غير متاحة حالياً. الرجاء المحاولة لاحقاً."
        diagnosis.status = DiagnosisStatus.FAILED
        diagnosis.error_message = friendly_error
        diagnosis.ai_metadata = {"engine_error": raw_error}
        diagnosis.save(update_fields=["status", "error_message", "ai_metadata", "updated_at"])

        log_audit_event(
            user=actor,
            university=getattr(case, "university", None),
            action="ai.diagnosis.failed",
            description="AI diagnosis failed",
            content_object=diagnosis,
            metadata={"error": raw_error},
        )
        return diagnosis, {"all_suggestions": [], "primary_suggestion": None, "next_suggestion": None}

    # Map payload safely
    suggestions_payload = _extract_suggestions(engine_payload)

    diagnosis.diagnosis_label = normalize_diagnosis_label(engine_payload.get("diagnosis_label"))
    diagnosis.primary_diagnosis = engine_payload.get("primary_diagnosis")
    diagnosis.detected_findings = engine_payload.get("detected_findings")
    diagnosis.patient_explanation = str(engine_payload.get("patient_explanation") or "")
    diagnosis.report_text = engine_payload.get("report_text")
    diagnosis.recommendations = engine_payload.get("recommendations")
    # Missing evidence must never become a reassuring default. Confidence,
    # severity and urgency are separate concepts and all remain ``unknown``
    # until the source explicitly supplies them.
    diagnosis.confidence_level = normalize_confidence(
        engine_payload.get("confidence_level"), default=ConfidenceLevel.UNKNOWN
    )
    diagnosis.severity_level = normalize_severity(
        engine_payload.get("severity_level"), default=SeverityLevel.UNKNOWN
    )
    diagnosis.urgency_level = normalize_urgency(
        engine_payload.get("urgency_level"), default=UrgencyLevel.UNKNOWN
    )
    raw_metadata = engine_payload.get("metadata") if isinstance(engine_payload.get("metadata"), dict) else {}
    # merge headline metadata into ai_metadata for audit
    merged_metadata = dict(raw_metadata or {})
    merged_metadata.setdefault("model_versions", engine_payload.get("model_versions"))
    merged_metadata.setdefault("flags", engine_payload.get("flags"))
    if suggestions_payload.get("all_suggestions"):
        merged_metadata["suggestions"] = suggestions_payload
    diagnosis.normalized_symptoms = (merged_metadata or {}).get("normalized_text") or diagnosis.normalized_symptoms
    fallback_mode = ((raw_metadata.get("fallback") or {}).get("mode")) if raw_metadata else None
    if not diagnosis.primary_diagnosis and not diagnosis.diagnosis_label:
        diagnosis.status = DiagnosisStatus.INSUFFICIENT_EVIDENCE
        diagnosis.error_message = "لم تُرجع الخدمة أدلة تشخيصية كافية. يلزم التقييم البشري."
        merged_metadata.setdefault("flags", {})["requires_supervisor_review"] = True
    elif fallback_mode and fallback_mode != "full":
        diagnosis.status = DiagnosisStatus.PARTIAL
        diagnosis.error_message = "التحليل غير مكتمل ويستلزم مراجعة مختص."
        merged_metadata.setdefault("flags", {})["requires_supervisor_review"] = True
    else:
        diagnosis.status = DiagnosisStatus.COMPLETED
        diagnosis.error_message = ""
    diagnosis.ai_metadata = build_ai_metadata(merged_metadata)
    diagnosis.save()

    log_audit_event(
        user=actor,
        university=getattr(case, "university", None),
        action=("ai.diagnosis.completed" if diagnosis.status == DiagnosisStatus.COMPLETED else "ai.diagnosis.insufficient_evidence"),
        description=("AI diagnosis completed" if diagnosis.status == DiagnosisStatus.COMPLETED else "AI diagnosis was not clinically complete"),
        content_object=diagnosis,
        metadata={"case_id": str(case.id)},
    )

    fallback_info = ((engine_payload.get("metadata") or {}).get("fallback")) if isinstance(engine_payload, dict) else None
    if isinstance(fallback_info, dict) and fallback_info.get("mode") != "full":
        log_audit_event(
            user=actor,
            university=getattr(case, "university", None),
            action="ai.diagnosis.fallback",
            description="AI diagnosis completed with fallback mode",
            content_object=diagnosis,
            metadata={"case_id": str(case.id), **fallback_info},
        )

    return diagnosis, suggestions_payload


@transaction.atomic
def review_ai_diagnosis(*, actor, diagnosis_id: str, approved: bool = True, note: str | None = None) -> AIDiagnosis:
    """
    Supervisor review flow: mark diagnosis as REVIEWED and append review metadata.
    """
    role = getattr(getattr(actor, "role", None), "name", None)
    if role != Role.SUPERVISOR:
        raise PermissionDenied("Only supervisors can review AI diagnoses.")

    diagnosis = (
        AIDiagnosis.objects.select_related("case", "patient", "requested_by")
        .select_for_update()
        .get(id=diagnosis_id)
    )

    if diagnosis.status not in (DiagnosisStatus.COMPLETED, DiagnosisStatus.PARTIAL, DiagnosisStatus.REVIEWED):
        raise PermissionDenied("Diagnosis must contain evidence before review.")

    case = getattr(diagnosis, "case", None)
    if not case or getattr(case, "supervisor_id", None) != actor.id:
        raise PermissionDenied("Supervisor can only review their assigned cases.")

    review_metadata = {
        "approved": approved,
        "note": note or "",
        "reviewed_by": str(actor.id),
        "reviewed_at": timezone.now().isoformat(),
    }

    metadata = diagnosis.ai_metadata or {}
    metadata["review"] = review_metadata

    diagnosis.status = DiagnosisStatus.REVIEWED
    diagnosis.reviewed_by = actor
    diagnosis.reviewed_at = timezone.now()
    diagnosis.ai_metadata = metadata
    diagnosis.save(update_fields=["status", "reviewed_by", "reviewed_at", "ai_metadata", "updated_at"])

    log_audit_event(
        user=actor,
        university=getattr(case, "university", None),
        action="ai.diagnosis.reviewed",
        description="Supervisor reviewed AI diagnosis",
        content_object=diagnosis,
        metadata={"case_id": str(case.id), "approved": approved, "note": note or ""},
    )

    return diagnosis
