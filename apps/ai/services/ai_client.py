import requests
from typing import Dict, List, Optional

from django.conf import settings
from django.utils.translation import gettext_lazy as _


# ============================================================
# EXCEPTIONS
# ============================================================

class AIEngineError(Exception):
    """
    Raised when AI Engine is unreachable, fails,
    or returns an invalid or incomplete response.
    """
    pass


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _post_to_ai_engine(
    *,
    endpoint: str,
    payload: Optional[dict] = None,
    files: Optional[dict] = None,
    timeout: int = 30,
) -> Dict:
    """
    Low-level HTTP client for AI Engine communication.

    Guarantees:
    - Network error handling
    - HTTP status validation
    - JSON response validation
    """

    base_url = settings.AI_ENGINE_URL.rstrip("/")
    url = f"{base_url}/{endpoint.lstrip('/')}"

    try:
        response = requests.post(
            url=url,
            json=payload if files is None else None,
            data=payload if files is not None else None,
            files=files,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise AIEngineError(_("AI engine is unreachable")) from exc

    if response.status_code != 200:
        raise AIEngineError(
            _("AI engine returned error (status: %(status)s)")
            % {"status": response.status_code}
        )

    try:
        return response.json()
    except ValueError as exc:
        raise AIEngineError(_("AI engine returned invalid JSON")) from exc


def _validate_required_fields(
    *,
    data: Dict,
    required_fields: set,
    context: str,
):
    """
    Enforce strict response contract from AI Engine.
    """
    if not required_fields.issubset(data.keys()):
        missing = required_fields - data.keys()
        raise AIEngineError(
            _("Invalid AI response for %(context)s. Missing fields: %(fields)s")
            % {
                "context": context,
                "fields": ", ".join(missing),
            }
        )


# ============================================================
# NLP MODEL CLIENT (AraBERT)
# ============================================================

def analyze_symptoms(symptoms_text: str) -> Dict:
    """
    Analyze Arabic symptom text using NLP model (AraBERT).

    Input:
        - symptoms_text: Arabic free-text symptoms

    Output:
        {
            "extracted_symptoms": [...],
            "severity_level": "low|moderate|high",
            "urgency_level": "non_urgent|urgent",
            "confidence_score": float,
            "metadata": {...}
        }
    """

    payload = {"text": symptoms_text}

    data = _post_to_ai_engine(
        endpoint="/nlp/analyze-symptoms",
        payload=payload,
    )

    required_fields = {
        "extracted_symptoms",
        "severity_level",
        "urgency_level",
        "confidence_score",
        "metadata",
    }

    _validate_required_fields(
        data=data,
        required_fields=required_fields,
        context="symptom analysis (AraBERT)",
    )

    return data


# ============================================================
# COMPUTER VISION MODEL CLIENT (YOLO)
# ============================================================

def analyze_dental_images(
    image_files: Optional[List],
) -> Optional[Dict]:
    """
    Analyze dental images using computer vision model (YOLO).

    Notes:
    - Image analysis is OPTIONAL.
    - If no images are provided, returns None.

    Output:
        {
            "teeth_findings": [
                {
                    "tooth_number": 6,
                    "finding": "caries",
                    "severity": "moderate",
                    "confidence": 0.78
                },
                ...
            ],
            "confidence_score": float,
            "metadata": {...}
        }
    """

    if not image_files:
        return None

    files = {
        f"image_{index}": image
        for index, image in enumerate(image_files)
    }

    data = _post_to_ai_engine(
        endpoint="/vision/analyze-teeth",
        files=files,
    )

    required_fields = {
        "teeth_findings",
        "confidence_score",
        "metadata",
    }

    _validate_required_fields(
        data=data,
        required_fields=required_fields,
        context="image analysis (YOLO)",
    )

    return data


# ============================================================
# FUSION MODEL CLIENT (BART)
# ============================================================

def fuse_ai_results(
    *,
    symptom_result: Dict,
    image_result: Optional[Dict],
) -> Dict:
    """
    Fuse NLP and Vision outputs using medical reasoning model (BART).

    IMPORTANT:
    - This function does NOT make decisions.
    - It only requests semantic fusion and report generation.

    Output:
        {
            "primary_diagnosis": str,
            "all_findings": [...],
            "report_text": str,
            "severity_level": "low|moderate|high",
            "urgency_level": "non_urgent|urgent",
            "confidence_level": "low|medium|high",
            "recommendations": str,
            "metadata": {...}
        }
    """

    payload = {
        "symptom_analysis": symptom_result,
        "image_analysis": image_result,
    }

    data = _post_to_ai_engine(
        endpoint="/fusion/diagnosis",
        payload=payload,
    )

    required_fields = {
        "primary_diagnosis",
        "all_findings",
        "report_text",
        "severity_level",
        "urgency_level",
        "confidence_level",
        "recommendations",
        "metadata",
    }

    _validate_required_fields(
        data=data,
        required_fields=required_fields,
        context="AI fusion (BART)",
    )

    return data
