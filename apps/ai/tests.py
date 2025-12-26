# apps/ai/tests.py
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.cases.models import Case
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
        payload = {"case_id": str(self.case.id), "symptoms_text": "أشعر بألم شديد في الضرس مع حساسية"}
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AIDiagnosis.objects.count(), 1)
        self.assertEqual(AIDiagnosis.objects.first().status, DiagnosisStatus.COMPLETED)

    def test_non_patient_cannot_request_ai_diagnosis(self):
        self.client.force_authenticate(user=self.student)
        url = reverse("ai:ai-diagnose")
        payload = {"case_id": str(self.case.id), "symptoms_text": "ألم في الأسنان"}
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
