from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.universities.models import University
from apps.reports.models import Report


class ReportModelTest(TestCase):
    """
    Test suite for Report model.
    Covers:
    - Creation
    - Role constraints
    - Defaults
    - String representation
    - Active flag behavior
    """

    def setUp(self):
        """
        Prepare common test objects.
        """
        self.university = University.objects.create(
            name="Test University",
            address="Test Address"
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student1@test.com",
            password="testpass123",
            role="student"
        )

        self.supervisor = User.objects.create_user(
            username="supervisor1",
            email="supervisor@test.com",
            password="testpass123",
            role="supervisor"
        )

        self.admin = User.objects.create_user(
            username="admin1",
            email="admin1@test.com",
            password="testpass123",
            role="university_admin"
        )

    # ============================================================
    # Creation
    # ============================================================

    def test_create_report_successfully(self):
        """
        Report should be created with valid data.
        """
        report = Report.objects.create(
            student=self.student,
            university=self.university,
            report_type="academic",
            file_url="https://example.com/report.pdf",
            generated_by=self.admin,
            title="Academic Performance Report",
            description="Semester performance summary"
        )

        self.assertEqual(report.student, self.student)
        self.assertEqual(report.university, self.university)
        self.assertEqual(report.report_type, "academic")
        self.assertEqual(report.generated_by, self.admin)
        self.assertTrue(report.is_active)
        self.assertIsNotNone(report.generated_at)
        self.assertIsNotNone(report.created_at)

    # ============================================================
    # Defaults & Flags
    # ============================================================

    def test_report_defaults(self):
        """
        Ensure default values are set correctly.
        """
        report = Report.objects.create(
            student=self.student,
            university=self.university,
            report_type="clinical",
            file_url="/reports/clinical.pdf"
        )

        self.assertTrue(report.is_active)
        self.assertIsNone(report.generated_by)
        self.assertIsNone(report.title)
        self.assertIsNone(report.description)

    # ============================================================
    # Constraints
    # ============================================================

    def test_report_requires_student_role(self):
        """
        Only users with role=student can be linked as report.student.
        """
        with self.assertRaises(Exception):
            Report.objects.create(
                student=self.admin,  # invalid role
                university=self.university,
                report_type="academic",
                file_url="/invalid.pdf"
            )

    # ============================================================
    # String Representation
    # ============================================================

    def test_report_string_representation(self):
        """
        __str__ should be human-readable and informative.
        """
        report = Report.objects.create(
            student=self.student,
            university=self.university,
            report_type="progress",
            file_url="/reports/progress.pdf"
        )

        text = str(report)
        self.assertIn(self.student.username, text)
        self.assertIn(self.university.name, text)

    # ============================================================
    # Soft Deactivation
    # ============================================================

    def test_deactivate_report(self):
        """
        Report can be soft-disabled without deletion.
        """
        report = Report.objects.create(
            student=self.student,
            university=self.university,
            report_type="attendance",
            file_url="/reports/attendance.pdf"
        )

        report.is_active = False
        report.save(update_fields=["is_active"])

        report.refresh_from_db()
        self.assertFalse(report.is_active)
