# apps/reports/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.universities.models import University
from apps.reports.models import Report
from apps.notifications.models import Notification
from apps.audit.models import AuditLog
from apps.cases.models import Case


class ReportsAPITest(APITestCase):

    def setUp(self):
        self.university = University.objects.create(name="Test Uni")

        self.student = User.objects.create_user(
            username="student",
            password="pass",
            role=Role.objects.get(name=Role.STUDENT),
            university=self.university,
        )

        self.supervisor = User.objects.create_user(
            username="supervisor",
            password="pass",
            role=Role.objects.get(name=Role.SUPERVISOR),
            university=self.university,
        )

        self.admin = User.objects.create_user(
            username="admin",
            password="pass",
            role=Role.objects.get(name=Role.UNIVERSITY_ADMIN),
            university=self.university,
        )

        self.tech = User.objects.create_user(
            username="tech",
            password="pass",
            role=Role.objects.get(name=Role.TECH_SUPPORT),
        )

        self.case = Case.objects.create(
            patient=self.student,  # simplified for test
            university=self.university,
            supervisor=self.supervisor,
            student=self.student,
        )

    # ---------------------------------------------------------
    # Permissions
    # ---------------------------------------------------------

    def test_student_can_view_own_reports_only(self):
        report = Report.objects.create(
            student=self.student,
            university=self.university,
            report_type="academic",
            file_url="/r.pdf",
        )

        self.client.force_authenticate(self.student)
        url = reverse("reports:report-detail", args=[report.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_student_cannot_generate_report(self):
        self.client.force_authenticate(self.student)
        url = reverse("reports:report-list")
        res = self.client.post(url, {})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_can_generate_report(self):
        self.client.force_authenticate(self.supervisor)
        url = reverse("reports:report-list")

        payload = {
            "student_id": str(self.student.id),
            "university_id": str(self.university.id),
            "report_type": "academic",
            "file_url": "/test.pdf",
        }

        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    # ---------------------------------------------------------
    # Business Rules
    # ---------------------------------------------------------

    def test_report_is_immutable(self):
        report = Report.objects.create(
            student=self.student,
            university=self.university,
            report_type="academic",
            file_url="/r.pdf",
        )

        report.title = "Hacked"
        with self.assertRaises(RuntimeError):
            report.save()

    # ---------------------------------------------------------
    # Audit + Notification
    # ---------------------------------------------------------

    def test_submit_report_creates_audit_and_notification(self):
        self.client.force_authenticate(self.student)

        url = reverse("reports:submit-report", args=[self.case.id])
        payload = {"content": "Case report content"}

        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Audit log created
        self.assertTrue(
            AuditLog.objects.filter(
                action="reports.report.submitted",
                user=self.student,
            ).exists()
        )

        # Notification sent to supervisor
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.supervisor,
                notification_type="report_submitted",
            ).exists()
        )
