# apps/ai/integrations/engine.py
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

AuditHook = Optional[Callable[[str, Dict[str, Any]], None]]


class AIEngineError(RuntimeError):
    pass


@dataclass(frozen=True)
class AIEngineConfig:
    base_url: str
    timeout_seconds: int = 30
    default_path: str = ""

    def build_url(self, path: Optional[str] = None) -> str:
        """
        Build a full URL while avoiding duplicate path segments when the base URL
        already contains the endpoint path (allows env to be base or full endpoint).
        """
        path_fragment = path if path is not None else self.default_path
        base = self.base_url.rstrip("/")
        if not path_fragment:
            return base

        normalized_path = path_fragment.lstrip("/")
        if base.endswith(f"/{normalized_path}"):
            return base
        return f"{base}/{normalized_path}"


@dataclass(frozen=True)
class AIEnginesConfig:
    symptoms: AIEngineConfig
    vision: AIEngineConfig
    fusion: AIEngineConfig


def _post_json(*, config: AIEngineConfig, path: Optional[str], payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        full_url = config.build_url(path)
        resp = requests.post(full_url, json=payload, timeout=config.timeout_seconds)
    except requests.RequestException as exc:
        raise AIEngineError(f"{config.base_url}: connection failed ({exc})") from exc

    if resp.status_code >= 400:
        raise AIEngineError(f"{full_url}: HTTP {resp.status_code} {resp.text}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise AIEngineError(f"{config.base_url}: invalid JSON response") from exc

    if not isinstance(data, dict):
        raise AIEngineError(f"{config.base_url}: unexpected payload type")

    return data


def _safe_audit(hook: AuditHook, action: str, metadata: Dict[str, Any]) -> None:
    if not hook:
        return
    try:
        hook(action, metadata)
    except Exception:
        logger.exception("Audit hook failed for %s", action)


def call_symptoms_model(
    *,
    config: AIEngineConfig,
    symptoms_text: str,
    case_id: Optional[str] = None,
    audit_hook: AuditHook = None,
) -> Dict[str, Any]:
    payload = {"symptoms_text": symptoms_text, "case_id": case_id}
    started = time.monotonic()
    try:
        data = _post_json(config=config, path=None, payload=payload)
        _safe_audit(
            audit_hook,
            "ai.call.symptoms.success",
            {
                "base_url": config.base_url,
                "endpoint": config.build_url(None),
                "duration_ms": int((time.monotonic() - started) * 1000),
                "case_id": case_id,
            },
        )
        return data
    except AIEngineError as exc:
        _safe_audit(
            audit_hook,
            "ai.call.symptoms.error",
            {
                "base_url": config.base_url,
                "endpoint": config.build_url(None),
                "duration_ms": int((time.monotonic() - started) * 1000),
                "case_id": case_id,
                "error": str(exc),
            },
        )
        raise


def call_vision_model(
    *,
    config: AIEngineConfig,
    image_urls: Optional[List[str]] = None,
    case_id: Optional[str] = None,
    audit_hook: AuditHook = None,
) -> Dict[str, Any]:
    payload = {"image_urls": image_urls or [], "case_id": case_id}
    started = time.monotonic()
    try:
        data = _post_json(config=config, path=None, payload=payload)
        _safe_audit(
            audit_hook,
            "ai.call.vision.success",
            {
                "base_url": config.base_url,
                "endpoint": config.build_url(None),
                "duration_ms": int((time.monotonic() - started) * 1000),
                "case_id": case_id,
                "images_count": len(image_urls or []),
            },
        )
        return data
    except AIEngineError as exc:
        _safe_audit(
            audit_hook,
            "ai.call.vision.error",
            {
                "base_url": config.base_url,
                "endpoint": config.build_url(None),
                "duration_ms": int((time.monotonic() - started) * 1000),
                "case_id": case_id,
                "images_count": len(image_urls or []),
                "error": str(exc),
            },
        )
        raise


def call_fusion_model(
    *,
    config: AIEngineConfig,
    symptoms_payload: Dict[str, Any],
    vision_payload: Dict[str, Any],
    symptoms_text: str,
    image_urls: Optional[List[str]] = None,
    case_id: Optional[str] = None,
    audit_hook: AuditHook = None,
) -> Dict[str, Any]:
    payload = {
        "case_id": case_id,
        "symptoms_text": symptoms_text,
        "image_urls": image_urls or [],
        "text_analysis": symptoms_payload,
        "image_analysis": vision_payload,
    }
    started = time.monotonic()
    try:
        data = _post_json(config=config, path=None, payload=payload)
        _safe_audit(
            audit_hook,
            "ai.call.fusion.success",
            {
                "base_url": config.base_url,
                "endpoint": config.build_url(None),
                "duration_ms": int((time.monotonic() - started) * 1000),
                "case_id": case_id,
                "payload_sizes": {
                    "text_analysis_keys": len(symptoms_payload or {}),
                    "image_analysis_keys": len(vision_payload or {}),
                },
            },
        )
        return data
    except AIEngineError as exc:
        _safe_audit(
            audit_hook,
            "ai.call.fusion.error",
            {
                "base_url": config.base_url,
                "endpoint": config.build_url(None),
                "duration_ms": int((time.monotonic() - started) * 1000),
                "case_id": case_id,
                "payload_sizes": {
                    "text_analysis_keys": len(symptoms_payload or {}),
                    "image_analysis_keys": len(vision_payload or {}),
                },
                "error": str(exc),
            },
        )
        raise


def analyze_case(
    *,
    configs: AIEnginesConfig,
    symptoms_text: str,
    image_urls: Optional[List[str]] = None,
    case_id: Optional[str] = None,
    audit_hook: AuditHook = None,
) -> Dict[str, Any]:
    """
    Orchestrates the three external engines (symptoms NLP, vision, fusion) and
    returns a unified payload consumable by services.

    Flow:
    1) Text analysis (AraBERT) via POST /analyze-symptoms
    2) Vision analysis (YOLO) via POST /analyze (optional if no images)
    3) Fusion of text+image via POST /analyze-case
    """
    symptoms_error: Optional[Exception] = None
    vision_error: Optional[Exception] = None
    fusion_error: Optional[Exception] = None
    fallback_mode = "full"

    symptoms_payload: Dict[str, Any] = {}
    try:
        symptoms_payload = call_symptoms_model(
            config=configs.symptoms, symptoms_text=symptoms_text, case_id=case_id, audit_hook=audit_hook
        )
    except AIEngineError as exc:
        symptoms_error = exc

    vision_payload: Dict[str, Any] = {}
    if image_urls:
        try:
            vision_payload = call_vision_model(
                config=configs.vision, image_urls=image_urls, case_id=case_id, audit_hook=audit_hook
            )
        except AIEngineError as exc:
            vision_error = exc

    if not symptoms_payload and not vision_payload:
        raise symptoms_error or vision_error or AIEngineError("AI engines unavailable")

    fusion_payload: Dict[str, Any] = {}
    try:
        fusion_payload = call_fusion_model(
            config=configs.fusion,
            symptoms_payload=symptoms_payload,
            vision_payload=vision_payload,
            symptoms_text=symptoms_text,
            image_urls=image_urls,
            case_id=case_id,
            audit_hook=audit_hook,
        )
    except AIEngineError as exc:
        fusion_error = exc
        if symptoms_payload and not vision_payload:
            fallback_mode = "text_only"
        elif vision_payload and not symptoms_payload:
            fallback_mode = "image_only"
        else:
            fallback_mode = "partial"

    normalized_text = (
        symptoms_payload.get("normalized_text")
        or symptoms_payload.get("normalized_symptoms")
        or symptoms_payload.get("clean_text")
    )
    decision_label = (
        fusion_payload.get("decision_label")
        or fusion_payload.get("diagnosis_label")
        or symptoms_payload.get("primary_condition")
    )
    primary_diagnosis = (
        fusion_payload.get("primary_diagnosis")
        or decision_label
        or symptoms_payload.get("primary_condition")
        or vision_payload.get("primary_finding")
    )
    detected_findings = (
        fusion_payload.get("detected_findings")
        or fusion_payload.get("findings")
        or fusion_payload.get("all_findings")
        or vision_payload.get("detected_findings")
        or symptoms_payload.get("suspected_conditions")
    )
    confidence = fusion_payload.get("confidence_level") or symptoms_payload.get("confidence_level")
    severity = (
        fusion_payload.get("severity_level")
        or fusion_payload.get("severity")
        or symptoms_payload.get("severity_level")
        or symptoms_payload.get("severity")
    )
    urgency = fusion_payload.get("urgency_level") or symptoms_payload.get("urgency_level")

    metadata = {
        "text_analysis": symptoms_payload,
        "image_analysis": vision_payload,
        "fusion_model": fusion_payload.get("metadata")
        if isinstance(fusion_payload.get("metadata"), dict)
        else fusion_payload,
        "normalized_text": normalized_text,
        "raw_payloads": {
            "symptoms": symptoms_payload,
            "vision": vision_payload,
            "fusion": fusion_payload,
        },
        "fallback": {
            "mode": fallback_mode,
            "symptoms_error": str(symptoms_error) if symptoms_error else None,
            "vision_error": str(vision_error) if vision_error else None,
            "fusion_error": str(fusion_error) if fusion_error else None,
        },
    }

    flags = fusion_payload.get("flags") or symptoms_payload.get("flags") or {}
    if fusion_error:
        flags = dict(flags or {})
        flags["fusion_error"] = str(fusion_error)
        flags["fallback_mode"] = fallback_mode

    return {
        "primary_diagnosis": primary_diagnosis,
        "diagnosis_label": decision_label,
        "detected_findings": detected_findings,
        "patient_explanation": fusion_payload.get("patient_explanation")
        or fusion_payload.get("patient_message")
        or symptoms_payload.get("patient_explanation"),
        "report_text": fusion_payload.get("medical_report") or fusion_payload.get("report_text"),
        "recommendations": fusion_payload.get("recommendations"),
        "confidence_level": confidence,
        "severity_level": severity,
        "urgency_level": urgency,
        "model_versions": fusion_payload.get("model_versions")
        or symptoms_payload.get("model_versions")
        or {"text_model": symptoms_payload.get("model")},
        "flags": flags,
        "metadata": metadata,
    }
