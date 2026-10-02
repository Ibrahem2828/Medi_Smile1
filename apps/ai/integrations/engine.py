# apps/ai/integrations/engine.py
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

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
    # Optional bearer token, needed e.g. for private Hugging Face Spaces.
    auth_token: str = field(default="", repr=False)

    def request_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}

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

        base_segments = [segment for segment in urlparse(base).path.split("/") if segment]
        path_segments = [segment for segment in normalized_path.split("/") if segment]
        overlap = 0
        for size in range(1, min(len(base_segments), len(path_segments)) + 1):
            if base_segments[-size:] == path_segments[:size]:
                overlap = size

        remaining_path = "/".join(path_segments[overlap:])
        return base if not remaining_path else f"{base}/{remaining_path}"


@dataclass(frozen=True)
class AIEnginesConfig:
    symptoms: AIEngineConfig
    vision: AIEngineConfig
    fusion: AIEngineConfig


@dataclass(frozen=True)
class ImageInput:
    """An image already held in memory (e.g. a validated patient upload)."""

    filename: str
    content: bytes
    content_type: str
    source_url: str


# Backwards-compatible alias for older imports.
_ImageUpload = ImageInput

# Hard cap on bytes read from a remote image URL (defence against huge bodies).
_MAX_REMOTE_IMAGE_BYTES = 10 * 1024 * 1024


def _download_first_image(image_urls: List[str], timeout: int) -> ImageInput:
    """
    Download the first reachable image so we can forward it as multipart/form-data
    to the vision model, which expects a binary file (see backend_endpoint.json).

    URLs reach this point only after the request serializer checked them against
    ``AI_IMAGE_URL_ALLOWED_HOSTS``; redirects are still refused so an allowed
    host cannot bounce the request to an internal address, and the body size is
    capped while streaming.
    """
    errors: List[str] = []
    for url in image_urls:
        try:
            with requests.get(url, timeout=timeout, stream=True, allow_redirects=False) as response:
                if response.status_code >= 300:
                    errors.append(f"{url}: HTTP {response.status_code}")
                    continue
                chunks: List[bytes] = []
                total = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    total += len(chunk)
                    if total > _MAX_REMOTE_IMAGE_BYTES:
                        raise AIEngineError(f"{url}: image exceeds {_MAX_REMOTE_IMAGE_BYTES} bytes")
                    chunks.append(chunk)
                content_type = (response.headers.get("content-type") or "").split(";")[0].strip()
        except requests.RequestException as exc:
            errors.append(f"{url}: {exc}")
            continue
        except AIEngineError as exc:
            errors.append(str(exc))
            continue

        filename = Path(urlparse(url).path).name or "image_upload"
        return ImageInput(
            filename=filename,
            content=b"".join(chunks),
            content_type=content_type or "application/octet-stream",
            source_url=url,
        )

    raise AIEngineError(f"Vision model: unable to fetch image from provided URLs ({'; '.join(errors)})")


def _post_multipart(
    *,
    config: AIEngineConfig,
    path: Optional[str],
    files: Dict[str, Any],
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    try:
        full_url = config.build_url(path)
        resp = requests.post(
            full_url,
            files=files,
            data=data or {},
            headers=config.request_headers(),
            timeout=config.timeout_seconds,
        )
    except requests.RequestException as exc:
        raise AIEngineError(f"{config.base_url}: connection failed ({exc})") from exc

    if resp.status_code >= 400:
        raise AIEngineError(f"{full_url}: HTTP {resp.status_code} {resp.text}")

    try:
        payload = resp.json()
    except ValueError as exc:
        raise AIEngineError(f"{config.base_url}: invalid JSON response") from exc

    if not isinstance(payload, dict):
        raise AIEngineError(f"{config.base_url}: unexpected payload type")

    return payload


def _post_json(*, config: AIEngineConfig, path: Optional[str], payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        full_url = config.build_url(path)
        resp = requests.post(
            full_url,
            json=payload,
            headers=config.request_headers(),
            timeout=config.timeout_seconds,
        )
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
    images: Optional[List[ImageInput]] = None,
    case_id: Optional[str] = None,
    audit_hook: AuditHook = None,
) -> Dict[str, Any]:
    """Analyze every supplied image and preserve the source of each result."""
    if images:
        uploads = list(images)
    elif image_urls:
        uploads = [_download_first_image([url], config.timeout_seconds) for url in image_urls]
    else:
        raise AIEngineError("Vision model requires at least one image.")

    results: list[dict[str, Any]] = []
    for upload in uploads:
        started = time.monotonic()
        try:
            data = _post_multipart(
                config=config,
                path=None,
                files={"image_file": (upload.filename, upload.content, upload.content_type)},
                data={"case_id": case_id or ""},
            )
            results.append({"image_id": upload.source_url, "analysis": data})
        except AIEngineError as exc:
            _safe_audit(
                audit_hook,
                "ai.call.vision.error",
                {
                    "base_url": config.base_url, "endpoint": config.build_url(None),
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "case_id": case_id, "image_source": upload.source_url, "error": str(exc),
                },
            )
            # A partial vision result is still useful as evidence, but its
            # missing images are explicit in the payload and force review.
            continue
        _safe_audit(
            audit_hook,
            "ai.call.vision.success",
            {
                "base_url": config.base_url,
                "endpoint": config.build_url(None),
                "duration_ms": int((time.monotonic() - started) * 1000),
                "case_id": case_id,
                "images_count": len(uploads),
                "image_source": upload.source_url,
            },
        )

    if not results:
        raise AIEngineError("Vision model did not return a usable result for any image.")
    if len(results) == 1 and len(uploads) == 1:
        return results[0]["analysis"]

    # Keep every finding attached to its image.  The flattened fields preserve
    # backward compatibility for a fusion service that currently accepts one
    # aggregate object, while ``image_results`` retains clinical traceability.
    findings = []
    for result in results:
        analysis = result["analysis"]
        for finding in analysis.get("detected_findings") or analysis.get("teeth") or []:
            findings.append({"image_id": result["image_id"], "finding": finding})
    first = results[0]["analysis"]
    return {
        "image_results": results,
        "images_requested": len(uploads),
        "images_analyzed": len(results),
        "primary_finding": first.get("primary_finding"),
        "detected_findings": findings,
    }


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


def _has_text_evidence(payload: Dict[str, Any]) -> bool:
    """Minimal semantic contract for the symptom service response."""
    if not isinstance(payload, dict):
        return False
    primary = payload.get("primary_condition")
    findings = payload.get("suspected_conditions")
    return bool(
        isinstance(primary, str) and primary.strip()
        or isinstance(findings, list) and any(isinstance(item, (dict, str)) for item in findings)
    )


def _has_vision_evidence(payload: Dict[str, Any]) -> bool:
    """Minimal semantic contract for the vision service response."""
    if not isinstance(payload, dict):
        return False
    primary = payload.get("primary_finding")
    findings = payload.get("detected_findings") or payload.get("teeth")
    per_image = payload.get("image_results")
    return bool(
        isinstance(primary, str) and primary.strip()
        or isinstance(findings, list) and len(findings)
        or isinstance(per_image, list) and len(per_image)
    )


def analyze_case(
    *,
    configs: AIEnginesConfig,
    symptoms_text: str,
    image_urls: Optional[List[str]] = None,
    images: Optional[List[ImageInput]] = None,
    case_id: Optional[str] = None,
    audit_hook: AuditHook = None,
) -> Dict[str, Any]:
    """
    Orchestrates the three external engines (symptoms NLP, vision, fusion) and
    returns a unified payload consumable by services.

    ``images`` are validated in-memory uploads; ``image_urls`` is the legacy
    (allow-listed) URL input. Either one enables the vision step.

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
        if not _has_text_evidence(symptoms_payload):
            raise AIEngineError("Symptoms model returned a payload without clinical evidence.")
    except AIEngineError as exc:
        symptoms_error = exc
        symptoms_payload = {}

    vision_payload: Dict[str, Any] = {}
    if images or image_urls:
        try:
            vision_payload = call_vision_model(
                config=configs.vision,
                image_urls=image_urls,
                images=images,
                case_id=case_id,
                audit_hook=audit_hook,
            )
            if not _has_vision_evidence(vision_payload):
                raise AIEngineError("Vision model returned a payload without clinical evidence.")
        except AIEngineError as exc:
            vision_error = exc
            vision_payload = {}
    image_refs = [img.source_url for img in (images or [])] or list(image_urls or [])

    if not symptoms_payload and not vision_payload:
        raise symptoms_error or vision_error or AIEngineError("AI engines unavailable")

    # The fusion engine needs BOTH modalities (its request schema requires
    # image_analysis and text_analysis). With only one, skip it deliberately
    # instead of provoking a 422 and reporting a spurious "fusion error".
    fusion_payload: Dict[str, Any] = {}
    if symptoms_payload and vision_payload:
        try:
            fusion_payload = call_fusion_model(
                config=configs.fusion,
                symptoms_payload=symptoms_payload,
                vision_payload=vision_payload,
                symptoms_text=symptoms_text,
                image_urls=image_refs,
                case_id=case_id,
                audit_hook=audit_hook,
            )
            parsed_fusion = parse_fusion_response(fusion_payload)
            if not parsed_fusion.get("final_diagnosis"):
                raise AIEngineError("Fusion model returned a payload without a valid proposal.")
        except AIEngineError as exc:
            fusion_error = exc
            fallback_mode = "partial"
    elif symptoms_payload:
        fallback_mode = "text_only"
    else:
        fallback_mode = "image_only"

    fusion = parse_fusion_response(fusion_payload)

    normalized_text = (
        symptoms_payload.get("normalized_text")
        or symptoms_payload.get("normalized_symptoms")
        or symptoms_payload.get("clean_text")
    )
    # diagnosis_label = the clinical concept (ontology id from fusion, else the
    # NLP/vision label). The fusion *decision* (high_match/…) is not a diagnosis
    # and is kept separately as match_label.
    primary_diagnosis = (
        fusion.get("final_diagnosis")
        or symptoms_payload.get("primary_condition")
        or vision_payload.get("primary_finding")
    )
    decision_label = primary_diagnosis
    detected_findings = (
        fusion.get("proposed_cases")
        or vision_payload.get("detected_findings")
        or vision_payload.get("teeth")
        or symptoms_payload.get("suspected_conditions")
    )
    confidence = fusion.get("confidence_level") or symptoms_payload.get("confidence_level")
    severity = (
        symptoms_payload.get("severity_level")
        or symptoms_payload.get("severity")
    )
    urgency = (
        fusion.get("urgency_level")
        or symptoms_payload.get("urgency_level")
        or symptoms_payload.get("urgency")
    )

    metadata = {
        "text_analysis": symptoms_payload,
        "image_analysis": vision_payload,
        "fusion_model": fusion_payload.get("metadata")
        if isinstance(fusion_payload.get("metadata"), dict)
        else fusion_payload,
        "normalized_text": normalized_text,
        "match_label": fusion.get("decision_label"),
        "requires_supervisor_review": fusion.get("requires_supervisor_review"),
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

    flags = dict(symptoms_payload.get("flags") or {})
    if fusion.get("safety_flags"):
        flags["safety_flags"] = fusion["safety_flags"]
    if fusion.get("requires_supervisor_review") is not None:
        flags["requires_supervisor_review"] = fusion["requires_supervisor_review"]
    if fallback_mode != "full":
        flags["fallback_mode"] = fallback_mode
    if fusion_error:
        flags["fusion_error"] = str(fusion_error)

    return {
        "primary_diagnosis": primary_diagnosis,
        "diagnosis_label": decision_label,
        "detected_findings": detected_findings,
        "fusion_results": fusion.get("proposed_cases") or [],
        "patient_explanation": fusion.get("summary") or symptoms_payload.get("patient_explanation"),
        "report_text": fusion.get("report_text"),
        "recommendations": fusion.get("recommendation"),
        "confidence_level": confidence,
        "severity_level": severity,
        "urgency_level": urgency,
        "model_versions": fusion.get("model_versions")
        or {
            "text_model": symptoms_payload.get("model_version") or symptoms_payload.get("model"),
            "vision_model": vision_payload.get("model_version") or vision_payload.get("model"),
        },
        "flags": flags,
        "metadata": metadata,
    }


def parse_fusion_response(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten the fusion engine's ``AnalyzeCaseResponse`` into the fields the
    backend stores. The engine returns::

        {"session_summary": {...}, "proposed_cases": [
            {"fusion_decision": {decision_label, final_diagnosis, confidence_level,
                                 urgency_level, requires_supervisor_review, safety_flags},
             "medical_report": {summary, recommendation, report_text, ...},
             "metadata": {"model_versions": {...}, ...}}, ...]}

    ``proposed_cases`` is already ordered by urgency then match score, so the
    first one is the headline. Returns ``{}`` for an empty/foreign payload.
    """
    if not isinstance(payload, dict):
        return {}
    proposals = [p for p in (payload.get("proposed_cases") or []) if isinstance(p, dict)]
    summary = payload.get("session_summary") if isinstance(payload.get("session_summary"), dict) else {}
    if not proposals and not summary:
        return {}

    head = proposals[0] if proposals else {}
    decision = head.get("fusion_decision") if isinstance(head.get("fusion_decision"), dict) else {}
    report = head.get("medical_report") if isinstance(head.get("medical_report"), dict) else {}
    meta = head.get("metadata") if isinstance(head.get("metadata"), dict) else {}

    requires_review = decision.get("requires_supervisor_review")
    if requires_review is None:
        requires_review = summary.get("requires_supervisor_review")

    return {
        "decision_label": decision.get("decision_label") or summary.get("overall_decision"),
        "final_diagnosis": decision.get("final_diagnosis"),
        "confidence_level": decision.get("confidence_level"),
        "urgency_level": decision.get("urgency_level"),
        "requires_supervisor_review": requires_review,
        "safety_flags": decision.get("safety_flags") or summary.get("safety_flags") or [],
        "summary": report.get("summary"),
        "recommendation": report.get("recommendation"),
        "report_text": report.get("report_text"),
        "model_versions": meta.get("model_versions"),
        "proposed_cases": proposals,
    }
