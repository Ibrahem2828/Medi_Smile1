# apps/cases/test_ai_critical_case.py
"""Only server-owned AI diagnoses can be routed to a university."""
from django.urls import reverse
from rest_framework import status

from apps.ai.models import AIDiagnosis
from apps.cases.models import Case
from medismile.testing import TwoUniversitiesTestCase

class AICriticalCaseCreateTests(TwoUniversitiesTestCase):
    url = reverse("ai-critical-case-create")

    def _auto_case_with_diagnosis(self, patient):
        case = Case.objects.create(patient=patient, title="AI Analysis - pain", description="pain")
        diagnosis = AIDiagnosis.objects.create(
            case=case,
            patient=patient,
            requested_by=patient,
            raw_symptoms="pain",
            status="completed",
            primary_diagnosis="caries_deep",
            confidence_level="high",
            severity_level="high",
            urgency_level="urgent",
        )
        return case, diagnosis

    def test_promotes_auto_created_case_instead_of_duplicating(self):
        case, diagnosis = self._auto_case_with_diagnosis(self.patient)
        self.login(self.patient)
        response = self.client.post(
            self.url, {"university_id": str(self.uni_a.id), "diagnosis_id": str(diagnosis.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["data"]["id"], str(case.id))
        case.refresh_from_db()
        self.assertEqual(case.university_id, self.uni_a.id)
        self.assertTrue(case.is_ai_critical)
        self.assertEqual(case.ai_metadata["source"], "server_ai_diagnosis")
        self.assertEqual(case.ai_metadata["diagnosis_id"], str(diagnosis.id))
        self.assertEqual(Case.objects.filter(patient=self.patient).count(), 1)

    def test_case_becomes_visible_to_that_university_only(self):
        _, diagnosis = self._auto_case_with_diagnosis(self.patient)
        self.login(self.patient)
        self.client.post(self.url, {"university_id": str(self.uni_a.id), "diagnosis_id": str(diagnosis.id)}, format="json")

        new_cases = reverse("supervisor-new-cases")
        self.login(self.supervisor_a)
        self.assertEqual(len(self.client.get(new_cases).data), 1)
        self.login(self.supervisor_b)
        self.assertEqual(len(self.client.get(new_cases).data), 0)

    def test_requires_a_server_diagnosis(self):
        self.login(self.patient)
        response = self.client.post(
            self.url,
            {"university_id": str(self.uni_b.id), "title": "Molar pain"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_cannot_reference_another_patients_diagnosis(self):
        _, foreign = self._auto_case_with_diagnosis(self.other_patient)
        self.login(self.patient)
        response = self.client.post(
            self.url,
            {"university_id": str(self.uni_a.id), "diagnosis_id": str(foreign.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_requires_active_university_and_rejects_client_report(self):
        _, diagnosis = self._auto_case_with_diagnosis(self.patient)
        self.login(self.patient)
        self.uni_b.is_active = False
        self.uni_b.save(update_fields=["is_active"])
        bad_uni = self.client.post(self.url, {"university_id": str(self.uni_b.id), "diagnosis_id": str(diagnosis.id)}, format="json")
        self.assertEqual(bad_uni.status_code, status.HTTP_400_BAD_REQUEST)
        client_report = self.client.post(
            self.url,
            {"university_id": str(self.uni_a.id), "diagnosis_id": str(diagnosis.id), "ai_report": {"primary_diagnosis": "forged"}},
            format="json",
        )
        self.assertEqual(client_report.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_patients(self):
        self.login(self.student_a)
        response = self.client.post(
            self.url, {"university_id": str(self.uni_a.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
