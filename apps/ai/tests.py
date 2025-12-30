# apps/ai/tests.py
from unittest.mock import patch
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.cases.models import Case
from apps.ai.constants import (
    build_ai_metadata,
    normalize_confidence,
    normalize_diagnosis_label,
    normalize_severity,
    normalize_urgency,
)
from apps.ai.integrations.endpoints import get_ai_engines_config
from apps.ai.models import AIDiagnosis, DiagnosisStatus


class AIDiagnosisAPITestCase(APITestCase):
    def setUp(self):
        # Roles (assume they exist in your DB; create if your tests run isolated)
        self.patient_role, _ = Role.objects.get_or_create(name=Role.PATIENT)
        self.student_role, _ = Role.objects.get_or_create(name=Role.STUDENT)

        self.patient = User.objects.create_user(
            email="patient@test.com",
            username="patient",
            password="password123",
            role=self.patient_role,
        )
        self.student = User.objects.create_user(
            email="student@test.com",
            username="student",
            password="password123",
            role=self.student_role,
        )

        self.case = Case.objects.create(
            patient=self.patient,
            title="Test Case",
            description="Dental pain case",
        )

    @patch("apps.ai.services.analyze_case")
    @patch("apps.ai.services._get_engine_config")
    def test_patient_can_request_ai_diagnosis(self, _cfg, analyze_case_mock):
        analyze_case_mock.return_value = {
            "primary_diagnosis": "تسوس متوسط",
            "diagnosis_label": "caries_moderate",
            "detected_findings": {"tooth": "16", "issue": "caries"},
            "patient_explanation": "يوجد تسوس يحتاج متابعة.",
            "report_text": "تفاصيل التقرير...",
            "recommendations": "زيارة العيادة خلال أسبوع.",
            "confidence_level": "medium",
            "severity_level": "moderate",
            "urgency_level": "non_urgent",
            "metadata": {"normalized_text": "الم في الضرس"},
        }

        self.client.force_authenticate(user=self.patient)
        url = reverse("ai:ai-diagnose")
        payload = {"symptoms_text": "أشعر بألم شديد في الضرس مع حساسية"}
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AIDiagnosis.objects.count(), 1)
        self.assertEqual(AIDiagnosis.objects.first().status, DiagnosisStatus.COMPLETED)

    def test_non_patient_cannot_request_ai_diagnosis(self):
        self.client.force_authenticate(user=self.student)
        url = reverse("ai:ai-diagnose")
        payload = {"symptoms_text": "ألم في الأسنان"}
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_can_list_own_diagnoses_only(self):
        AIDiagnosis.objects.create(
            case=self.case,
            patient=self.patient,
            requested_by=self.patient,
            raw_symptoms="ألم مستمر",
            diagnosis_label="internal_tooth_pain",
            primary_diagnosis="تسوس متوسط في الضرس الخلفي",
            patient_explanation="يوجد تسوس يحتاج متابعة",
            status=DiagnosisStatus.COMPLETED,
        )

        self.client.force_authenticate(user=self.patient)
        url = reverse("ai:ai-diagnosis-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)


class AIEndpointsConfigTestCase(APITestCase):
    @override_settings(
        AI_SYMPTOMS_URL="http://ai.local/symptoms",
        AI_VISION_URL="http://ai.local/vision",
        AI_FUSION_URL="http://ai.local/fusion",
        AI_ENGINE_TIMEOUT=15,
    )
    def test_endpoints_are_read_from_settings(self):
        cfg = get_ai_engines_config()
        self.assertEqual(cfg.symptoms.base_url, "http://ai.local/symptoms")
        self.assertEqual(cfg.vision.base_url, "http://ai.local/vision")
        self.assertEqual(cfg.fusion.base_url, "http://ai.local/fusion")
        self.assertEqual(cfg.symptoms.timeout_seconds, 15)
        self.assertEqual(cfg.symptoms.build_url(None), "http://ai.local/symptoms/analyze-symptoms")
        self.assertEqual(cfg.vision.build_url(None), "http://ai.local/vision/analyze")
        self.assertEqual(cfg.fusion.build_url(None), "http://ai.local/fusion/analyze-case")

    @override_settings(
        AI_SYMPTOMS_URL="http://ai.local/symptoms/analyze-symptoms",
        AI_VISION_URL="http://ai.local/vision/analyze",
        AI_FUSION_URL="http://ai.local/fusion/analyze-case",
    )
    def test_build_url_does_not_double_append_path(self):
        cfg = get_ai_engines_config()
        self.assertEqual(cfg.symptoms.build_url(None), "http://ai.local/symptoms/analyze-symptoms")
        self.assertEqual(cfg.vision.build_url(None), "http://ai.local/vision/analyze")
        self.assertEqual(cfg.fusion.build_url(None), "http://ai.local/fusion/analyze-case")


class AINormalizationHelpersTestCase(APITestCase):
    def test_normalization_helpers_use_defaults(self):
        self.assertEqual(normalize_diagnosis_label("caries"), "dental_caries")
        self.assertEqual(normalize_diagnosis_label(None), "")
        self.assertEqual(normalize_confidence(None, default="medium"), "medium")
        self.assertEqual(normalize_severity("moderate", default="low"), "moderate")
        self.assertEqual(normalize_urgency("urgent", default="non_urgent"), "urgent")

    def test_build_ai_metadata_preserves_raw_and_normalized(self):
        raw = {
            "normalized_text": "cleaned symptoms",
            "match_label": "caries",
            "model_versions": {"fusion": "1.0"},
            "raw_payloads": {"symptoms": {"x": 1}},
        }
        built = build_ai_metadata(raw)
        self.assertEqual(built["normalized_text"], "cleaned symptoms")
        self.assertEqual(built["match_label"], "caries")
        self.assertEqual(built["model_versions"], {"fusion": "1.0"})
        self.assertIn("raw_payloads", built)
        self.assertIn("engine_metadata", built)


class AIReviewFlowAPITestCase(APITestCase):
    def setUp(self):
        self.patient_role, _ = Role.objects.get_or_create(name=Role.PATIENT)
        self.supervisor_role, _ = Role.objects.get_or_create(name=Role.SUPERVISOR)

        self.patient = User.objects.create_user(
            email="patient2@test.com",
            username="patient2",
            password="password123",
            role=self.patient_role,
        )
        self.supervisor = User.objects.create_user(
            email="super@test.com",
            username="supervisor",
            password="password123",
            role=self.supervisor_role,
        )

        self.case = Case.objects.create(
            patient=self.patient,
            supervisor=self.supervisor,
            title="Reviewable Case",
            description="Dental case for review",
        )

        self.diagnosis = AIDiagnosis.objects.create(
            case=self.case,
            patient=self.patient,
            requested_by=self.patient,
            raw_symptoms="Pain in molar",
            diagnosis_label="caries",
            status=DiagnosisStatus.COMPLETED,
        )

    def test_supervisor_can_review_own_case_diagnosis(self):
        self.client.force_authenticate(user=self.supervisor)
        url = reverse("ai:ai-diagnosis-review", kwargs={"pk": str(self.diagnosis.id)})
        res = self.client.post(url, {"approved": True, "note": "looks good"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.diagnosis.refresh_from_db()
        self.assertEqual(self.diagnosis.status, DiagnosisStatus.REVIEWED)
        self.assertEqual(self.diagnosis.reviewed_by_id, self.supervisor.id)
        self.assertIn("review", self.diagnosis.ai_metadata or {})

    def test_non_supervisor_cannot_review(self):
        self.client.force_authenticate(user=self.patient)
        url = reverse("ai:ai-diagnosis-review", kwargs={"pk": str(self.diagnosis.id)})
        res = self.client.post(url, {"approved": True}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MyAnalysisAPITestCase(APITestCase):
    def setUp(self):
        self.patient_role, _ = Role.objects.get_or_create(name=Role.PATIENT)
        self.student_role, _ = Role.objects.get_or_create(name=Role.STUDENT)

        self.patient = User.objects.create_user(
            email="patient3@test.com",
            username="patient3",
            password="password123",
            role=self.patient_role,
        )
        self.student = User.objects.create_user(
            email="student3@test.com",
            username="student3",
            password="password123",
            role=self.student_role,
        )

    def _auth_patient(self):
        self.client.force_authenticate(user=self.patient)

    def test_returns_latest_analysis_for_patient(self):
        case = Case.objects.create(patient=self.patient, title="AI Case", description="desc")
        diagnosis = AIDiagnosis.objects.create(
            case=case,
            patient=self.patient,
            requested_by=self.patient,
            raw_symptoms="tooth pain",
            primary_diagnosis="abscess",
            diagnosis_label="abscess_label",
            severity_level="high",
            confidence_level="high",
            urgency_level="urgent",
            patient_explanation="تشير نتائج التحليل إلى احتمال وجود خراج سني.",
            recommendations="ننصحك بمراجعة طبيب الأسنان في أقرب وقت.",
            status=DiagnosisStatus.COMPLETED,
        )

        self._auth_patient()
        url = reverse("ai:ai-my-analysis")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["case_id"], str(case.id))
        self.assertEqual(res.data["status"], "analyzed")
        self.assertEqual(res.data["ai_summary"]["suspected_condition"], "abscess")
        self.assertEqual(res.data["ai_summary"]["severity"], diagnosis.severity_level)
        self.assertEqual(res.data["ai_summary"]["confidence_level"], diagnosis.confidence_level)
        self.assertEqual(res.data["ai_summary"]["urgency_level"], diagnosis.urgency_level)

    def test_returns_processing_when_no_diagnosis(self):
        Case.objects.create(patient=self.patient, title="AI Case", description="desc")
        self._auth_patient()
        url = reverse("ai:ai-my-analysis")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(res.data["status"], "processing")

    def test_returns_processing_when_pending(self):
        case = Case.objects.create(patient=self.patient, title="AI Case", description="desc")
        AIDiagnosis.objects.create(
            case=case,
            patient=self.patient,
            requested_by=self.patient,
            raw_symptoms="pain",
            status=DiagnosisStatus.PENDING,
        )
        self._auth_patient()
        url = reverse("ai:ai-my-analysis")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(res.data["status"], "processing")

    def test_non_patient_forbidden(self):
        self.client.force_authenticate(user=self.student)
        url = reverse("ai:ai-my-analysis")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_found_when_no_case(self):
        self._auth_patient()
        url = reverse("ai:ai-my-analysis")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
