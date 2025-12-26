# apps/ai/services.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.models import Role
from apps.audit.services import log_audit_event
from apps.cases.models import Case

from .models import AIDiagnosis, DiagnosisStatus
from .integrations.engine import AIEngineConfig, AIEngineError, analyze_case


def _get_engine_config() -> AIEngineConfig:
    # Put in settings:
    # AI_ENGINE_BASE_URL="http://127.0.0.1:8001" (FastAPI)
    base_url = getattr(settings, "AI_ENGINE_BASE_URL", "").strip()
    if not base_url:
        # واضح وصريح لتجنب "import engine" / إعداد ناقص
        raise RuntimeError("AI_ENGINE_BASE_URL is not configured in settings.")
    return AIEngineConfig(
        base_url=base_url,
        timeout_seconds=int(getattr(settings, "AI_ENGINE_TIMEOUT", 30)),
    )


@transaction.atomic
def request_ai_diagnosis(
    *,
    actor,
    case_id,
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

    case = Case.objects.select_related("university").get(id=case_id, patient=actor)

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
            config=_get_engine_config(),
            symptoms_text=symptoms_text,
            image_urls=image_urls or [],
            case_id=str(case.id),
        )
    except AIEngineError as exc:
        diagnosis.status = DiagnosisStatus.FAILED
        diagnosis.error_message = str(exc)
        diagnosis.save(update_fields=["status", "error_message", "updated_at"])

        log_audit_event(
            user=actor,
            university=getattr(case, "university", None),
            action="ai.diagnosis.failed",
            description="AI diagnosis failed",
            content_object=diagnosis,
            metadata={"error": str(exc)},
        )
        return diagnosis

    # Map payload safely
    diagnosis.diagnosis_label = str(engine_payload.get("diagnosis_label") or "")
    diagnosis.primary_diagnosis = engine_payload.get("primary_diagnosis")
    diagnosis.detected_findings = engine_payload.get("detected_findings")
    diagnosis.patient_explanation = str(engine_payload.get("patient_explanation") or "")
    diagnosis.report_text = engine_payload.get("report_text")
    diagnosis.recommendations = engine_payload.get("recommendations")
    diagnosis.confidence_level = engine_payload.get("confidence_level") or diagnosis.confidence_level
    diagnosis.severity_level = engine_payload.get("severity_level") or diagnosis.severity_level
    diagnosis.urgency_level = engine_payload.get("urgency_level") or diagnosis.urgency_level
    diagnosis.normalized_symptoms = (
        (engine_payload.get("metadata") or {}).get("normalized_text")
        if isinstance(engine_payload.get("metadata"), dict)
        else diagnosis.normalized_symptoms
    )
    diagnosis.ai_metadata = engine_payload.get("metadata") if isinstance(engine_payload.get("metadata"), dict) else diagnosis.ai_metadata
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

    return diagnosis
