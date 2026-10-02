"""
Shared AI normalization constants.

These mappings keep external model outputs aligned with the internal
domain language used by the Django app.
"""
from __future__ import annotations

from typing import Any, Dict

from .models import ConfidenceLevel, SeverityLevel, UrgencyLevel

DIAGNOSIS_LABEL_MAP: Dict[str, str] = {
    # Technical label from engine -> internal/system label
    "caries": "dental_caries",
    "caries_moderate": "dental_caries_moderate",
    "caries_severe": "dental_caries_severe",
    "gingivitis": "gingivitis",
}

# Normalization for choice-like fields. Keys are external labels, values are internal enums.
CONFIDENCE_LEVEL_MAP: Dict[str, str] = {
    "unknown": ConfidenceLevel.UNKNOWN,
    "low": ConfidenceLevel.LOW,
    "medium": ConfidenceLevel.MEDIUM,
    "high": ConfidenceLevel.HIGH,
}

SEVERITY_LEVEL_MAP: Dict[str, str] = {
    "unknown": SeverityLevel.UNKNOWN,
    "low": SeverityLevel.LOW,
    "mild": SeverityLevel.LOW,
    "moderate": SeverityLevel.MODERATE,
    "medium": SeverityLevel.MODERATE,  # NLP / fusion vocabulary
    "high": SeverityLevel.HIGH,
    "severe": SeverityLevel.HIGH,
}

# Engines speak different vocabularies: NLP returns "Urgent"/"Non-Urgent",
# fusion returns low/medium/high urgency. Only "high" is urgent.
URGENCY_LEVEL_MAP: Dict[str, str] = {
    "unknown": UrgencyLevel.UNKNOWN,
    "non_urgent": UrgencyLevel.NON_URGENT,
    "urgent": UrgencyLevel.URGENT,
    "high": UrgencyLevel.URGENT,
    "medium": UrgencyLevel.NON_URGENT,
    "low": UrgencyLevel.NON_URGENT,
}


def normalize_diagnosis_label(label: str | None) -> str:
    if not label:
        return ""
    return DIAGNOSIS_LABEL_MAP.get(label, label)


def _normalize_choice(value: str | None, mapping: Dict[str, str], default: str) -> str:
    if not value:
        return default
    key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return mapping.get(key, default)


def normalize_confidence(value: str | None, default: str) -> str:
    return _normalize_choice(value, CONFIDENCE_LEVEL_MAP, default)


def normalize_severity(value: str | None, default: str) -> str:
    return _normalize_choice(value, SEVERITY_LEVEL_MAP, default)


def normalize_urgency(value: str | None, default: str) -> str:
    return _normalize_choice(value, URGENCY_LEVEL_MAP, default)


def build_ai_metadata(raw_metadata: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Normalize and structure AI metadata without losing raw payloads.
    """
    if not isinstance(raw_metadata, dict):
        return {}

    normalized_text = raw_metadata.get("normalized_text") or raw_metadata.get("normalized_symptoms")
    match_label = raw_metadata.get("match_label")
    model_versions = raw_metadata.get("model_versions") or {}
    flags = raw_metadata.get("flags") or {}

    structured = {
        "normalized_text": normalized_text,
        "match_label": match_label,
        "model_versions": model_versions,
        "flags": flags,
    }

    # Keep raw payloads under a dedicated key for audit/debug
    raw_payloads = raw_metadata.get("raw_payloads") or {}
    if raw_payloads:
        structured["raw_payloads"] = raw_payloads

    # Preserve engine-provided metadata for traceability
    structured["engine_metadata"] = raw_metadata

    return structured
