# apps/ai/integrations/engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import requests


class AIEngineError(RuntimeError):
    pass


@dataclass(frozen=True)
class AIEngineConfig:
    base_url: str
    timeout_seconds: int = 30


def analyze_case(
    *,
    config: AIEngineConfig,
    symptoms_text: str,
    image_urls: Optional[List[str]] = None,
    case_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calls external AI Engine.
    Expected response (example):
    {
      "primary_diagnosis": "...",
      "diagnosis_label": "...",
      "detected_findings": {...},
      "patient_explanation": "...",
      "report_text": "...",
      "recommendations": "...",
      "confidence_level": "medium",
      "severity_level": "moderate",
      "urgency_level": "non_urgent",
      "metadata": {...}
    }
    """
    payload = {
        "case_id": case_id,
        "symptoms_text": symptoms_text,
        "image_urls": image_urls or [],
    }

    try:
        resp = requests.post(
            f"{config.base_url.rstrip('/')}/analyze",
            json=payload,
            timeout=config.timeout_seconds,
        )
    except requests.RequestException as exc:
        raise AIEngineError(f"AI Engine connection failed: {exc}") from exc

    if resp.status_code >= 400:
        raise AIEngineError(f"AI Engine error: {resp.status_code} {resp.text}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise AIEngineError("AI Engine returned invalid JSON") from exc

    if not isinstance(data, dict):
        raise AIEngineError("AI Engine returned invalid payload type")

    return data
