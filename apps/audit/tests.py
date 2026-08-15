# apps/audit/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.universities.models import University
from apps.audit.models import AuditLog, AuditAction


class AuditLogAPITestCase(APITestCase):
    @staticmethod
    def _create_user_with_university(*, role, university, **fields):
        user = User(role=role, **fields)
        user._desired_university_id = university.id
        user.set_password(fields.pop("password"))
        user.save()
        return user

    def setUp(self):
        # Roles (avoid duplicates if seeded)
        self.university_admin_role, _ = Role.objects.get_or_create(name=Role.UNIVERSITY_ADMIN)
        self.tech_support_role, _ = Role.objects.get_or_create(name=Role.TECH_SUPPORT)
        self.student_role, _ = Role.objects.get_or_create(name=Role.STUDENT)

        self.university = University.objects.create(name="Audit Test University")

        self.university_admin = self._create_user_with_university(
            email="admin@test.com",
            username="admin",
            password="password123",
            role=self.university_admin_role,
            university=self.university,
        )

        self.tech_support = User.objects.create_user(
            email="tech@test.com",
            username="tech",
            password="password123",
            role=self.tech_support_role,
        )

        self.student = self._create_user_with_university(
            email="student@test.com",
            username="student",
            password="password123",
            role=self.student_role,
            university=self.university,
        )

        # Logs: one for admin scope, one global tech
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

    def test_university_admin_can_list_scoped_audit_logs(self):
        self.client.force_authenticate(user=self.university_admin)
        url = reverse("audit:audit-log-list")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Must be scoped to university (both logs are in same university here => 2)
        self.assertEqual(len(res.data), 2)

    def test_tech_support_can_list_all_logs(self):
        self.client.force_authenticate(user=self.tech_support)
        url = reverse("audit:audit-log-list")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 2)

    def test_student_cannot_access_audit_logs(self):
        self.client.force_authenticate(user=self.student)
        url = reverse("audit:audit-log-list")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_audit_statistics_endpoint(self):
        self.client.force_authenticate(user=self.university_admin)
        url = reverse("audit:audit-statistics")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("action_counts", res.data)
        self.assertIn("top_users", res.data)
        self.assertIn("daily_activity", res.data)

    def test_filter_by_action(self):
        self.client.force_authenticate(user=self.tech_support)
        url = reverse("audit:audit-log-list") + f"?action={AuditAction.CREATE}"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(all(item["action"] == AuditAction.CREATE for item in res.data))
