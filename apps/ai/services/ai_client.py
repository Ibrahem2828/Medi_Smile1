import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class AIEngineError(Exception):
    """Raised when AI Engine fails or returns invalid response."""


def analyze_symptoms_via_ai_engine(symptoms_text: str) -> dict:
    """
    Call external AI Engine (FastAPI) for symptom analysis.
    """

    try:
        response = requests.post(
            settings.AI_ENGINE_URL,
            json={"text": symptoms_text},
            timeout=30,  # مهم جدًا
        )
    except requests.RequestException as exc:
        raise AIEngineError(_("AI engine is unreachable")) from exc

    if response.status_code != 200:
        raise AIEngineError(
            _("AI engine returned error: %(status)s")
            % {"status": response.status_code}
        )

    data = response.json()

    # تحقق صارم (Contract validation)
    required_fields = {
        "diagnosis_label",
        "confidence_level",
        "severity_level",
        "urgency_level",
        "patient_explanation",
        "recommendations",
        "metadata",
    }

    if not required_fields.issubset(data.keys()):
        raise AIEngineError(_("Invalid AI response format"))

    return data
