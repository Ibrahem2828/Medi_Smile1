from django.test import TestCase
from apps.accounts.models import User
from apps.universities.models import University
from .models import Report


class ReportModelTest(TestCase):
    """Test cases for Report model."""
    
    def setUp(self):
        """Set up test data."""
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
        self.admin = User.objects.create_user(
            username="admin1",
            email="admin1@test.com",
            password="testpass123",
            role="university_admin"
        )
    
    def test_create_report(self):
        """Test creating a report."""
        report = Report.objects.create(
            student=self.student,
            university=self.university,
            report_type='academic',
            file_url='https://example.com/report.pdf',
            generated_by=self.admin
        )
        self.assertEqual(report.student, self.student)
        self.assertEqual(report.university, self.university)
        self.assertEqual(report.report_type, 'academic')
        self.assertIsNotNone(report.generated_at)


