# apps/evaluations/tests.py
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.universities.models import University
from apps.cases.models import Case
from apps.evaluations.models import Evaluation, EvaluationStatus


class EvaluationAPITestCase(APITestCase):
    def setUp(self):
        self.university = University.objects.create(name="Test University")

        self.supervisor = User.objects.create_user(
            username="supervisor",
            email="supervisor@test.com",
            password="password123",
            role=Role.objects.get(name=Role.SUPERVISOR),
            university=self.university,
        )

        self.student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="password123",
            role=Role.objects.get(name=Role.STUDENT),
            university=self.university,
        )

        # IMPORTANT: adapt to your Case model fields
        self.case = Case.objects.create(
            university=self.university,
            patient=self.student if hasattr(Case, "patient") else None,
            student=self.student if hasattr(Case, "student") else None,
            status=getattr(Case.Status, "IN_PROGRESS", "in_progress") if hasattr(Case, "Status") else "in_progress",
        )

        self.client.force_authenticate(user=self.supervisor)

    def test_supervisor_can_create_case_evaluation(self):
        url = reverse("evaluations-list")

        payload = {
            "student_id": str(self.student.id),
            "target_type": "case",
            "case_id": str(self.case.id),
            "score": 85,
            "comment": "Good clinical performance",
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Evaluation.objects.count(), 1)

    def test_student_cannot_create_evaluation(self):
        self.client.force_authenticate(user=self.student)
        url = reverse("evaluations-list")

        payload = {
            "student_id": str(self.student.id),
            "target_type": "case",
            "case_id": str(self.case.id),
            "score": 90,
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_submit_and_finalize_evaluation(self):
        evaluation = Evaluation.objects.create(
            university=self.university,
            evaluator=self.supervisor,
            student=self.student,
            target_type="case",
            case=self.case,
            score=88,
        )

        submit_url = reverse("evaluations-submit", args=[evaluation.id])
        finalize_url = reverse("evaluations-finalize", args=[evaluation.id])

        response_submit = self.client.post(submit_url)
        self.assertEqual(response_submit.status_code, status.HTTP_200_OK)
        evaluation.refresh_from_db()
        self.assertEqual(evaluation.status, EvaluationStatus.SUBMITTED)

        response_finalize = self.client.post(finalize_url)
        self.assertEqual(response_finalize.status_code, status.HTTP_200_OK)
        evaluation.refresh_from_db()
        self.assertEqual(evaluation.status, EvaluationStatus.FINAL)

    def test_final_evaluation_cannot_be_modified(self):
        evaluation = Evaluation.objects.create(
            university=self.university,
            evaluator=self.supervisor,
            student=self.student,
            target_type="case",
            case=self.case,
            score=92,
            status=EvaluationStatus.FINAL,
            finalized_at=timezone.now(),
        )

        url = reverse("evaluations-detail", args=[evaluation.id])
        payload = {"score": 60}
        response = self.client.patch(url, payload, format="json")
        self.assertIn(response.status_code, {status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST})
