# apps/ai/test_engine_contract.py
"""
Backend <-> AI engines contract.

``test_data/fusion_analyze_case_response.json`` is a *real* response produced by
the fusion engine (ai_services/fusion_engine, POST /fusion/analyze-case) for a
payload shaped exactly as the backend forwards the NLP and vision outputs.
Regenerate it if the fusion response schema changes.
"""
import json
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.ai.constants import normalize_severity, normalize_urgency
from apps.ai.integrations.endpoints import get_ai_engines_config
from apps.ai.integrations.engine import (
    AIEngineConfig,
    AIEnginesConfig,
    ImageInput,
    analyze_case,
    parse_fusion_response,
)
from apps.ai.models import SeverityLevel, UrgencyLevel

FUSION_RESPONSE = json.loads(
    (Path(__file__).parent / "test_data" / "fusion_analyze_case_response.json").read_text(encoding="utf-8")
)

NLP_RESPONSE = {
    "case_id": "c1",
    "suspected_conditions": [{"name": "خراج سني", "confidence": 0.8}],
    "severity": "High",
    "model_version": "arabert_symptoms_v1",
    "primary_condition": "خراج سني",
    "confidence_level": "high",
    "normalized_text": "تورم وقيح",
    "urgency_level": "Urgent",
    "patient_explanation": "يرجى مراجعة الطبيب بشكل عاجل.",
    "metadata": {},
}

VISION_RESPONSE = {"image_quality": "good", "primary_finding": "cavity", "model": "yolov8m"}

CONFIGS = AIEnginesConfig(
    symptoms=AIEngineConfig(base_url="http://nlp.test/analyze-symptoms"),
    vision=AIEngineConfig(base_url="http://vision.test/vision/analyze"),
    fusion=AIEngineConfig(base_url="http://fusion.test/fusion/analyze-case"),
)

IMAGE = ImageInput(filename="a.jpg", content=b"\xff\xd8fake", content_type="image/jpeg", source_url="ai-upload:1")


class ParseFusionResponseTests(SimpleTestCase):
    def test_extracts_headline_decision_from_real_response(self):
        parsed = parse_fusion_response(FUSION_RESPONSE)
        head = FUSION_RESPONSE["proposed_cases"][0]
        self.assertEqual(parsed["decision_label"], head["fusion_decision"]["decision_label"])
        self.assertEqual(parsed["final_diagnosis"], head["fusion_decision"]["final_diagnosis"])
        self.assertEqual(parsed["urgency_level"], head["fusion_decision"]["urgency_level"])
        self.assertEqual(parsed["requires_supervisor_review"], head["fusion_decision"]["requires_supervisor_review"])
        self.assertEqual(parsed["report_text"], head["medical_report"]["report_text"])
        self.assertEqual(parsed["summary"], head["medical_report"]["summary"])
        self.assertEqual(parsed["model_versions"], head["metadata"]["model_versions"])
        self.assertEqual(len(parsed["proposed_cases"]), len(FUSION_RESPONSE["proposed_cases"]))

    def test_empty_or_foreign_payload(self):
        self.assertEqual(parse_fusion_response({}), {})
        self.assertEqual(parse_fusion_response({"unexpected": 1}), {})
        self.assertEqual(parse_fusion_response(None), {})


class AnalyzeCaseOrchestrationTests(SimpleTestCase):
    @patch("apps.ai.integrations.engine.call_fusion_model", return_value=FUSION_RESPONSE)
    @patch("apps.ai.integrations.engine.call_vision_model", return_value=VISION_RESPONSE)
    @patch("apps.ai.integrations.engine.call_symptoms_model", return_value=NLP_RESPONSE)
    def test_full_mode_uses_fusion_decision(self, _nlp, vision_mock, fusion_mock):
        result = analyze_case(configs=CONFIGS, symptoms_text="تورم وقيح في اللثة", images=[IMAGE])
        head = FUSION_RESPONSE["proposed_cases"][0]["fusion_decision"]
        self.assertEqual(result["primary_diagnosis"], head["final_diagnosis"])
        self.assertEqual(result["diagnosis_label"], head["final_diagnosis"])
        self.assertEqual(result["metadata"]["match_label"], head["decision_label"])
        self.assertEqual(result["urgency_level"], head["urgency_level"])
        self.assertEqual(result["metadata"]["fallback"]["mode"], "full")
        self.assertTrue(result["fusion_results"])
        self.assertEqual(vision_mock.call_args.kwargs["images"], [IMAGE])
        fusion_mock.assert_called_once()

    @patch("apps.ai.integrations.engine.call_fusion_model")
    @patch("apps.ai.integrations.engine.call_symptoms_model", return_value=NLP_RESPONSE)
    def test_text_only_skips_fusion_and_keeps_nlp_urgency(self, _nlp, fusion_mock):
        result = analyze_case(configs=CONFIGS, symptoms_text="تورم وقيح في اللثة")
        fusion_mock.assert_not_called()
        self.assertEqual(result["metadata"]["fallback"]["mode"], "text_only")
        self.assertIsNone(result["metadata"]["fallback"]["fusion_error"])
        self.assertEqual(result["primary_diagnosis"], "خراج سني")
        self.assertEqual(normalize_urgency(result["urgency_level"], default=UrgencyLevel.NON_URGENT), UrgencyLevel.URGENT)
        self.assertEqual(result["patient_explanation"], NLP_RESPONSE["patient_explanation"])


class NormalizationVocabularyTests(SimpleTestCase):
    def test_urgency_vocabularies(self):
        for value, expected in (
            ("Urgent", UrgencyLevel.URGENT),
            ("Non-Urgent", UrgencyLevel.NON_URGENT),
            ("high", UrgencyLevel.URGENT),
            ("medium", UrgencyLevel.NON_URGENT),
            ("low", UrgencyLevel.NON_URGENT),
        ):
            self.assertEqual(normalize_urgency(value, default="?"), expected, value)

    def test_severity_vocabularies(self):
        self.assertEqual(normalize_severity("High", default="?"), SeverityLevel.HIGH)
        self.assertEqual(normalize_severity("medium", default="?"), SeverityLevel.MODERATE)
        self.assertEqual(normalize_severity("Low", default="?"), SeverityLevel.LOW)


class FusionEndpointPathTests(SimpleTestCase):
    def test_fusion_url_resolves_to_router_path_for_any_configured_form(self):
        for configured in (
            "http://fusion.test",
            "http://fusion.test/fusion",
            "http://fusion.test/fusion/analyze-case",
        ):
            with self.subTest(configured=configured), override_settings(AI_FUSION_URL=configured):
                self.assertEqual(
                    get_ai_engines_config().fusion.build_url(None),
                    "http://fusion.test/fusion/analyze-case",
                )
