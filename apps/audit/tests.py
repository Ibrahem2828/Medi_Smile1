# apps/audit/tests.py

from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.universities.models import University
from apps.audit.models import AuditLog, AuditAction


class AuditLogAPITestCase(APITestCase):

    def setUp(self):
        # Roles
        self.university_admin_role = Role.objects.create(name=Role.UNIVERSITY_ADMIN)
        self.tech_support_role = Role.objects.create(name=Role.TECH_SUPPORT)
        self.student_role = Role.objects.create(name=Role.STUDENT)

        # University
        self.university = University.objects.create(name="Audit Test University")

        # Users
        self.university_admin = User.objects.create_user(
            email="admin@test.com",
            username="admin",
            password="password123",
            role=self.university_admin_role,
        )

        self.tech_support = User.objects.create_user(
            email="tech@test.com",
            username="tech",
            password="password123",
            role=self.tech_support_role,
        )

        self.student = User.objects.create_user(
            email="student@test.com",
            username="student",
            password="password123",
            role=self.student_role,
        )

        # Create audit logs
        AuditLog.objects.create(
            user=self.university_admin,
            university=self.university,
            action=AuditAction.CREATE,
            description="Created a test object",
            metadata={"object": "test"},
            ip_address="127.0.0.1",
            user_agent="TestAgent",
        )

        AuditLog.objects.create(
            user=self.tech_support,
            university=self.university,
            action=AuditAction.UPDATE,
            description="Updated a test object",
            metadata={"field": "name"},
            ip_address="127.0.0.1",
            user_agent="TestAgent",
        )

    def test_university_admin_can_list_audit_logs(self):
        self.client.force_authenticate(user=self.university_admin)

        url = reverse("audit-log-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_tech_support_can_list_audit_logs(self):
        self.client.force_authenticate(user=self.tech_support)

        url = reverse("audit-log-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_student_cannot_access_audit_logs(self):
        self.client.force_authenticate(user=self.student)

        url = reverse("audit-log-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_audit_statistics_endpoint(self):
        self.client.force_authenticate(user=self.university_admin)

        url = reverse("audit-statistics")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn("action_counts", response.data)
        self.assertIn("top_users", response.data)
        self.assertIn("daily_activity", response.data)
