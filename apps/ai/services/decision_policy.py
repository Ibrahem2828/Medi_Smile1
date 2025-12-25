from typing import Dict, List, Optional
from django.utils.translation import gettext_lazy as _


class DecisionPolicyError(Exception):
    """
    Raised when the decision policy cannot produce
    a safe and coherent diagnosis report.
    """
    pass


def build_final_diagnosis(
    *,
    symptom_analysis: Dict,
    image_analysis: Optional[Dict],
    fusion_result: Dict,
) -> Dict:
    """
    Build a COMPLETE and DETAILED AI diagnosis report.

    Design principles:
    - One PRIMARY diagnosis (headline)
    - Multiple detected problems (structured)
    - One unified medical report (not fragmented)
    - Clear, honest, patient-safe language
    """

    # --------------------------------------------------
    # 1. Contract validation
    # --------------------------------------------------
    required_fusion_fields = {
        "primary_diagnosis",
        "all_findings",
        "severity_level",
        "urgency_level",
        "confidence_level",
        "report_text",
        "recommendations",
        "metadata",
    }

    if not required_fusion_fields.issubset(fusion_result.keys()):
        raise DecisionPolicyError(
            _("Fusion result does not satisfy full diagnosis contract")
        )

    # --------------------------------------------------
    # 2. Extract fusion outputs
    # --------------------------------------------------
    primary_diagnosis = fusion_result["primary_diagnosis"]
    all_findings: List[Dict] = fusion_result["all_findings"]

    severity_level = fusion_result["severity_level"]
    urgency_level = fusion_result["urgency_level"]
    confidence_level = fusion_result["confidence_level"]

    report_text = fusion_result["report_text"]
    recommendations = fusion_result.get("recommendations")

    # --------------------------------------------------
    # 3. Defensive consistency adjustments
    # --------------------------------------------------

    # If images exist but no visual findings → downgrade confidence
    if image_analysis is not None:
        teeth_findings = image_analysis.get("teeth_findings", [])
        if not teeth_findings and confidence_level == "high":
            confidence_level = "medium"

    # If symptoms indicate high severity but no images provided
    if image_analysis is None:
        if symptom_analysis.get("severity_level") == "high":
            urgency_level = "urgent"

    # --------------------------------------------------
    # 4. Sort findings by clinical importance
    # --------------------------------------------------
    def _finding_priority(finding: Dict) -> int:
        """
        Higher number = higher priority
        """
        return {
            "high": 3,
            "moderate": 2,
            "low": 1,
        }.get(finding.get("severity"), 0)

    sorted_findings = sorted(
        all_findings,
        key=_finding_priority,
        reverse=True,
    )

    # --------------------------------------------------
    # 5. Final unified output
    # --------------------------------------------------
    final_output = {
        # Headline diagnosis (one only)
        "primary_diagnosis": primary_diagnosis,

        # Structured list of all detected problems
        "detected_findings": sorted_findings,

        # Human-readable detailed report
        "patient_explanation": report_text,

        # Guidance
        "recommendations": recommendations,

        # Risk & confidence
        "severity_level": severity_level,
        "urgency_level": urgency_level,
        "confidence_level": confidence_level,

        # Internal trace (hidden from patient UI if needed)
        "ai_metadata": {
            "symptom_analysis": symptom_analysis,
            "image_analysis": image_analysis,
            "fusion_metadata": fusion_result.get("metadata"),
        },
    }

    return final_output
