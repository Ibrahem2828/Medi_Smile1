"""
Centralized AI engine endpoints.

This keeps the URLs for each external model (symptoms/NLP, vision, fusion)
in one place so operations and DevOps can update targets without touching
business logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from django.conf import settings

from .engine import AIEngineConfig, AIEnginesConfig


@dataclass(frozen=True)
class EndpointDoc:
    method: str
    path: str
    summary: str
    usage: str
    used_in_backend: bool = False


@dataclass(frozen=True)
class _EndpointConfig:
    key: str
    label: str
    setting_names: List[str]
    default_path: str


def _pick_first_configured_url(setting_names: List[str]) -> str:
    for name in setting_names:
        value = getattr(settings, name, "").strip()
        if value:
            return value
    return ""


def _build_configurations() -> AIEnginesConfig:
    """
    Returns concrete configs for the three external engines:
    - Symptoms / NLP (AraBERT or equivalent) -> primary contract: POST /analyze-symptoms
    - Vision (YOLO or equivalent) -> POST /analyze
    - Fusion (decision + report writer) -> POST /analyze-case

    Notes:
    - Env vars can point to a base URL or the fully qualified endpoint; build_url()
      will avoid double-appending the default path.
    """
    endpoint_matrix = [
        _EndpointConfig(
            key="symptoms",
            label="symptoms (AraBERT)",
            setting_names=["AI_SYMPTOMS_URL", "AI_ARABERT_URL"],
            default_path="analyze-symptoms",
        ),
        _EndpointConfig(
            key="vision",
            label="vision (YOLO)",
            setting_names=["AI_VISION_URL", "AI_YOLO_URL"],
            default_path="vision/analyze",
        ),
        _EndpointConfig(
            key="fusion",
            label="fusion engine",
            setting_names=["AI_FUSION_URL", "AI_ENGINE_BASE_URL"],
            # The fusion service mounts its router under /fusion (app/main.py).
            # build_url() de-duplicates, so AI_FUSION_URL may be the bare host,
            # ".../fusion" or the full ".../fusion/analyze-case".
            default_path="fusion/analyze-case",
        ),
    ]

    urls = {}
    default_paths = {}
    missing_labels = []
    for entry in endpoint_matrix:
        url = _pick_first_configured_url(entry.setting_names)
        if not url:
            missing_labels.append(entry.label)
        urls[entry.key] = url
        default_paths[entry.key] = entry.default_path

    if missing_labels:
        missing_str = ", ".join(missing_labels)
        raise RuntimeError(f"AI endpoints are not configured for: {missing_str}")

    timeout = int(getattr(settings, "AI_ENGINE_TIMEOUT", 30))

    # Map back using labels to keep the loop readable above
    return AIEnginesConfig(
        symptoms=AIEngineConfig(
            base_url=urls["symptoms"], timeout_seconds=timeout, default_path=default_paths["symptoms"]
        ),
        vision=AIEngineConfig(
            base_url=urls["vision"], timeout_seconds=timeout, default_path=default_paths["vision"]
        ),
        fusion=AIEngineConfig(
            base_url=urls["fusion"], timeout_seconds=timeout, default_path=default_paths["fusion"]
        ),
    )


def get_ai_engines_config() -> AIEnginesConfig:
    """
    Public accessor used by services.
    Separated for clarity and to allow lazy initialization/testing.
    """
    return _build_configurations()


# Reference: AraBERT symptoms service contract (Model #2)
# This mirrors the doc shared by the ML team so backend engineers can
# cross-check the contract without leaving the codebase.
ARABERT_SYMPTOMS_API: Tuple[EndpointDoc, ...] = (
    EndpointDoc(
        method="GET",
        path="/",
        summary="Index endpoint to confirm the service is reachable.",
        usage="Manual ping only; never used in Django logic.",
        used_in_backend=False,
    ),
    EndpointDoc(
        method="GET",
        path="/health",
        summary="Lightweight health probe to verify the model is loaded and ready.",
        usage="Startup checks / monitoring",
        used_in_backend=False,
    ),
    EndpointDoc(
        method="POST",
        path="/api/analyze-text",
        summary="Raw debugging endpoint for free-form text analysis.",
        usage="Debug/testing only; excluded from production flows.",
        used_in_backend=False,
    ),
    EndpointDoc(
        method="POST",
        path="/analyze/symptoms",
        summary="Legacy/simple symptoms analyzer returning a direct display-ready result.",
        usage="Early UI prototypes; not part of the final medical flow.",
        used_in_backend=False,
    ),
    EndpointDoc(
        method="POST",
        path="/analyze-symptoms",
        summary="Primary contract used by Django -> AraBERT -> Fusion pipeline.",
        usage="Always called from Django; output is forwarded to the Fusion engine.",
        used_in_backend=True,
    ),
)

# Reference: Fusion engine contract (Model #3)
FUSION_ENGINE_API: Tuple[EndpointDoc, ...] = (
    EndpointDoc(
        method="POST",
        path="/analyze-case",
        summary="Final decision and medical report generation engine.",
        usage="Receives text + image analysis and returns medical report.",
        used_in_backend=True,
    ),
)


def list_configured_ai_endpoints() -> dict:
    """
    DX helper to expose current AI endpoint wiring for debugging/admin panels.
    Returns base URL, resolved endpoint (with default path), and timeout.
    """
    cfg = get_ai_engines_config()
    return {
        "symptoms": {
            "base_url": cfg.symptoms.base_url,
            "endpoint": cfg.symptoms.build_url(None),
            "timeout_seconds": cfg.symptoms.timeout_seconds,
        },
        "vision": {
            "base_url": cfg.vision.base_url,
            "endpoint": cfg.vision.build_url(None),
            "timeout_seconds": cfg.vision.timeout_seconds,
        },
        "fusion": {
            "base_url": cfg.fusion.base_url,
            "endpoint": cfg.fusion.build_url(None),
            "timeout_seconds": cfg.fusion.timeout_seconds,
        },
    }
