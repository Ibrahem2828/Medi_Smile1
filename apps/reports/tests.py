# apps/reports/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role, StudentProfile, SupervisorProfile, UniversityAdminProfile, PatientProfile
from apps.universities.models import University
from apps.cases.models import Case
from apps.reports.models import Report


class ReportsAPITest(APITestCase):

    def setUp(self):
        self.university = University.objects.create(name="Test Uni")

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
            university=self.university,
            supervisor=self.supervisor,
            student=self.student,
        )

    def test_student_create_submit_and_supervisor_approve(self):
        self.client.force_authenticate(self.student)
        create_url = reverse("reports:report-list")
        payload = {
            "report_type": "clinical_case",
            "target_type": "case",
            "target_id": str(self.case.id),
            "content": {"summary": "Case summary"},
        }

        res = self.client.post(create_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        report_id = res.data["id"]

        submit_url = reverse("reports:report-submit", args=[report_id])
        res = self.client.post(submit_url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], Report.Status.SUBMITTED)

        self.client.force_authenticate(self.supervisor)
        approve_url = reverse("reports:report-approve", args=[report_id])
        res = self.client.post(approve_url, {"review_notes": "Good"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], Report.Status.LOCKED)

    def test_student_cannot_update_after_approval(self):
        report = Report.objects.create(
            author=self.student,
            author_role=Role.STUDENT,
            student=self.student,
            university=self.university,
            report_type=Report.ReportType.CLINICAL_CASE,
            target_type=Report.TargetType.CASE,
            target_id=self.case.id,
            content={"summary": "x"},
            status=Report.Status.LOCKED,
            approved_by=self.supervisor,
            approved_at=None,
        )

        self.client.force_authenticate(self.student)
        url = reverse("reports:report-detail", args=[report.id])
        res = self.client.patch(url, {"title": "Updated"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_can_view_case_report(self):
        report = Report.objects.create(
            author=self.student,
            author_role=Role.STUDENT,
            student=self.student,
            university=self.university,
            report_type=Report.ReportType.CLINICAL_CASE,
            target_type=Report.TargetType.CASE,
            target_id=self.case.id,
            content={"summary": "x"},
            status=Report.Status.LOCKED,
            approved_by=self.supervisor,
        )

        self.client.force_authenticate(self.patient)
        url = reverse("reports:report-detail", args=[report.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
