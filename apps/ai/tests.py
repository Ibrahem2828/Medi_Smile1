# apps/ai/tests.py

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.cases.models import Case
from apps.ai.models import AIDiagnosis


class AIDiagnosisAPITestCase(APITestCase):

    def setUp(self):
        # Roles
        self.patient_role = Role.objects.create(name=Role.PATIENT)
        self.student_role = Role.objects.create(name=Role.STUDENT)

        # Users
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

        # Case
        self.case = Case.objects.create(
            patient=self.patient,
            title="Test Case",
            description="Dental pain case",
        )

        self.analyze_url = reverse("ai-analyze-symptoms")

    def test_patient_can_request_ai_analysis(self):
        self.client.force_authenticate(user=self.patient)

        payload = {
            "case_id": str(self.case.id),
            "symptoms_text": "أشعر بألم شديد في الضرس مع حساسية عند الأكل",
        }

        response = self.client.post(self.analyze_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AIDiagnosis.objects.count(), 1)

        diagnosis = AIDiagnosis.objects.first()
        self.assertEqual(diagnosis.patient, self.patient)
        self.assertEqual(diagnosis.case, self.case)

    def test_non_patient_cannot_request_ai_analysis(self):
        self.client.force_authenticate(user=self.student)

        payload = {
            "case_id": str(self.case.id),
            "symptoms_text": "ألم في الأسنان",
        }

        response = self.client.post(self.analyze_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_can_list_own_ai_diagnoses(self):
        self.client.force_authenticate(user=self.patient)

        AIDiagnosis.objects.create(
            case=self.case,
            patient=self.patient,
            requested_by=self.patient,
            raw_symptoms="ألم مستمر",
            diagnosis_label="tooth_pain",
            confidence_level="medium",
            severity_level="moderate",
            urgency_level="non_urgent",
            patient_explanation="قد يكون هناك تسوس",
            status="completed",
        )

        url = reverse("ai-diagnosis-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
