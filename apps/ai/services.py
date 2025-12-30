# apps/ai/services.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

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
from .models import (
    AIDiagnosis,
    ConfidenceLevel,
    DiagnosisStatus,
    SeverityLevel,
    UrgencyLevel,
)
from .integrations.endpoints import get_ai_engines_config
from .integrations.engine import AIEngineError, AIEnginesConfig, analyze_case


def _get_engine_config() -> AIEnginesConfig:
    """
    Returns configuration for the three AI engines (symptoms, vision, fusion).
    Resolved centrally in integrations.endpoints.
    """
    return get_ai_engines_config()


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


@transaction.atomic
def request_ai_diagnosis(
    *,
    actor,
    case_id=None,
    patient_id=None,
    symptoms_text: str,
    image_urls: Optional[List[str]] = None,
) -> AIDiagnosis:
    """
    Patient-only: create AIDiagnosis by calling external AI engine.
    Also logs audit for request/result/failure.
    """
    role = getattr(getattr(actor, "role", None), "name", None)
    if role != Role.PATIENT:
        raise PermissionDenied("Only patients can request AI diagnosis.")

    if patient_id and str(patient_id) != str(getattr(actor, "id", None)):
        raise PermissionDenied("Patient ID does not match the authenticated user.")

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

    log_audit_event(
        user=actor,
        university=getattr(case, "university", None),
        action="ai.diagnosis.requested",
        description="Patient requested AI diagnosis",
        content_object=diagnosis,
        metadata={"case_id": str(case.id)},
    )

    try:
        engine_payload: Dict[str, Any] = analyze_case(
            configs=_get_engine_config(),
            symptoms_text=symptoms_text,
            image_urls=image_urls or [],
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
        return diagnosis

    # Map payload safely
    diagnosis.diagnosis_label = normalize_diagnosis_label(engine_payload.get("diagnosis_label"))
    diagnosis.primary_diagnosis = engine_payload.get("primary_diagnosis")
    diagnosis.detected_findings = engine_payload.get("detected_findings")
    diagnosis.patient_explanation = str(engine_payload.get("patient_explanation") or "")
    diagnosis.report_text = engine_payload.get("report_text")
    diagnosis.recommendations = engine_payload.get("recommendations")
    diagnosis.confidence_level = normalize_confidence(
        engine_payload.get("confidence_level"), default=ConfidenceLevel.MEDIUM
    )
    diagnosis.severity_level = normalize_severity(
        engine_payload.get("severity_level"), default=SeverityLevel.MODERATE
    )
    diagnosis.urgency_level = normalize_urgency(
        engine_payload.get("urgency_level"), default=UrgencyLevel.NON_URGENT
    )
    raw_metadata = engine_payload.get("metadata") if isinstance(engine_payload.get("metadata"), dict) else {}
    # merge headline metadata into ai_metadata for audit
    merged_metadata = dict(raw_metadata or {})
    merged_metadata.setdefault("model_versions", engine_payload.get("model_versions"))
    merged_metadata.setdefault("flags", engine_payload.get("flags"))
    diagnosis.normalized_symptoms = (merged_metadata or {}).get("normalized_text") or diagnosis.normalized_symptoms
    diagnosis.ai_metadata = build_ai_metadata(merged_metadata)
    diagnosis.status = DiagnosisStatus.COMPLETED
    diagnosis.error_message = ""
    diagnosis.save()

    log_audit_event(
        user=actor,
        university=getattr(case, "university", None),
        action="ai.diagnosis.completed",
        description="AI diagnosis completed",
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

    return diagnosis


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

    if diagnosis.status not in (DiagnosisStatus.COMPLETED, DiagnosisStatus.REVIEWED):
        raise PermissionDenied("Diagnosis must be completed before review.")

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
