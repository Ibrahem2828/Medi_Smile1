# apps/evaluations/tests.py
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import (
    PatientProfile,
    Role,
    StudentProfile,
    SupervisorProfile,
    UniversityAdminProfile,
    User,
)
from apps.appointments.models import Appointment
from apps.cases.models import Case
from apps.universities.models import University
from apps.evaluations.models import Evaluation, EvaluationStatus, EvaluationTargetType


class EvaluationAPITestCase(APITestCase):
    def setUp(self):
        self.university = University.objects.create(name="Test University")

        self.student_role, _ = Role.objects.get_or_create(name=Role.STUDENT)
        self.supervisor_role, _ = Role.objects.get_or_create(name=Role.SUPERVISOR)
        self.admin_role, _ = Role.objects.get_or_create(name=Role.UNIVERSITY_ADMIN)
        self.patient_role, _ = Role.objects.get_or_create(name=Role.PATIENT)

        self.student = User.objects.create_user(
            username="student",
            password="pass",
            role=self.student_role,
        )
        StudentProfile.objects.create(user=self.student, university=self.university)

        self.supervisor = User.objects.create_user(
            username="supervisor",
            password="pass",
            role=self.supervisor_role,
        )
        SupervisorProfile.objects.create(user=self.supervisor, university=self.university)

        self.admin = User.objects.create_user(
            username="admin",
            password="pass",
            role=self.admin_role,
        )
        UniversityAdminProfile.objects.create(user=self.admin, university=self.university)

        self.patient = User.objects.create_user(
            username="patient",
            password="pass",
            role=self.patient_role,
        )
        PatientProfile.objects.create(user=self.patient, university=self.university)

        self.case = Case.objects.create(
            title="Case",
            description="Desc",
            patient=self.patient,
            student=self.student,
            supervisor=self.supervisor,
            university=self.university,
        )

        self.appointment = Appointment.objects.create(
            case=self.case,
            patient=self.patient,
            student=self.student,
            supervisor=self.supervisor,
            created_by=self.student,
            appointment_date=timezone.now(),
        )

    def test_patient_can_create_appointment_evaluation(self):
        self.client.force_authenticate(self.patient)
        url = reverse("evaluations:evaluations-list")
        payload = {
            "target_type": "appointment",
            "target_id": str(self.appointment.id),
            "original_score": 85,
            "comment": "Great experience",
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Evaluation.objects.count(), 1)

    def test_student_can_create_case_evaluation(self):
        self.client.force_authenticate(self.student)
        url = reverse("evaluations:evaluations-list")
        payload = {
            "target_type": "case",
            "target_id": str(self.case.id),
            "original_score": 70,
            "comment": "Self review",
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Evaluation.objects.count(), 1)

    def test_supervisor_can_adjust_evaluation(self):
        evaluation = Evaluation.objects.create(
            university=self.university,
            evaluator=self.patient,
            evaluator_role=Role.PATIENT,
            student=self.student,
            target_type=EvaluationTargetType.APPOINTMENT,
            target_id=self.appointment.id,
            appointment=self.appointment,
            score=80,
            final_score=80,
            status=EvaluationStatus.CREATED,
        )

        self.client.force_authenticate(self.supervisor)
        url = reverse("evaluations:evaluations-adjust", args=[evaluation.id])
        payload = {"new_score": 90, "reason": "Adjusted after review"}

        response = self.client.patch(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        evaluation.refresh_from_db()
        self.assertEqual(evaluation.status, EvaluationStatus.ADJUSTED)
        self.assertEqual(evaluation.final_score, 90)

    def test_admin_can_finalize_evaluation(self):
        evaluation = Evaluation.objects.create(
            university=self.university,
            evaluator=self.supervisor,
            evaluator_role=Role.SUPERVISOR,
            student=self.student,
            target_type=EvaluationTargetType.STUDENT,
            target_id=self.student.id,
            score=88,
            final_score=88,
            status=EvaluationStatus.UNDER_REVIEW,
        )

        self.client.force_authenticate(self.admin)
        url = reverse("evaluations:evaluations-finalize", args=[evaluation.id])

        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        evaluation.refresh_from_db()
        self.assertEqual(evaluation.status, EvaluationStatus.FINALIZED)

    def test_student_rating_endpoint(self):
        Evaluation.objects.create(
            university=self.university,
            evaluator=self.patient,
            evaluator_role=Role.PATIENT,
            student=self.student,
            target_type=EvaluationTargetType.STUDENT,
            target_id=self.student.id,
            score=80,
            final_score=80,
            status=EvaluationStatus.FINALIZED,
        )
        Evaluation.objects.create(
            university=self.university,
            evaluator=self.supervisor,
            evaluator_role=Role.SUPERVISOR,
            student=self.student,
            target_type=EvaluationTargetType.STUDENT,
            target_id=self.student.id,
            score=90,
            final_score=90,
            status=EvaluationStatus.FINALIZED,
        )
        Evaluation.objects.create(
            university=self.university,
            evaluator=self.admin,
            evaluator_role=Role.UNIVERSITY_ADMIN,
            student=self.student,
            target_type=EvaluationTargetType.STUDENT,
            target_id=self.student.id,
            score=70,
            final_score=70,
            status=EvaluationStatus.FINALIZED,
        )

        self.client.force_authenticate(self.supervisor)
        url = reverse("evaluations:student-evaluation-rating", args=[self.student.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["final_rating"], 82.5)
