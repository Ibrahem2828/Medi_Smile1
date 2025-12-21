# apps/evaluations/tests.py

from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
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
            role="supervisor",
            university=self.university,
        )

        self.student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="password123",
            role="student",
            university=self.university,
        )

        self.case = Case.objects.create(
            patient_name="Test Patient",
            student=self.student,
            university=self.university,
            status="active",
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

        evaluation = Evaluation.objects.first()
        self.assertEqual(evaluation.student, self.student)
        self.assertEqual(evaluation.evaluator, self.supervisor)
        self.assertEqual(evaluation.status, EvaluationStatus.DRAFT)

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

    def test_student_can_view_own_evaluations_only(self):
        evaluation = Evaluation.objects.create(
            university=self.university,
            evaluator=self.supervisor,
            student=self.student,
            target_type="case",
            case=self.case,
            score=75,
        )

        self.client.force_authenticate(user=self.student)
        url = reverse("evaluations-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

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
        self.assertIsNotNone(evaluation.submitted_at)

        response_finalize = self.client.post(finalize_url)
        self.assertEqual(response_finalize.status_code, status.HTTP_200_OK)

        evaluation.refresh_from_db()
        self.assertEqual(evaluation.status, EvaluationStatus.FINAL)
        self.assertIsNotNone(evaluation.finalized_at)

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
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
