# apps/backup/tests.py
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.backup.models import Backup
from apps.audit.models import AuditLog


class BackupAPITest(APITestCase):

    def setUp(self):
        tech_role, _ = Role.objects.get_or_create(name=Role.TECH_SUPPORT)
        student_role, _ = Role.objects.get_or_create(name=Role.STUDENT)
        self.tech = User.objects.create_user(
            username="tech",
            email="tech@example.test",
            password="pass",
            role=tech_role,
        )

        self.student = User.objects.create_user(
            username="student",
            email="student@example.test",
            password="pass",
            role=student_role,
        )

    def test_tech_support_can_create_backup(self):
        self.client.force_authenticate(self.tech)

        url = reverse("backup-run-backup")
        payload = {
            "backup_type": "database",
            "description": "Daily DB backup",
        }

        with patch("apps.backup.views.run_backup_task.delay") as mocked_task:
            response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(Backup.objects.count(), 1)

        backup = Backup.objects.first()
        self.assertEqual(backup.created_by, self.tech)
        self.assertEqual(backup.status, Backup.Status.IN_PROGRESS)

        # Task triggered
        mocked_task.assert_called_once()

        # Audit created
        self.assertTrue(
            AuditLog.objects.filter(
                action="backup.created",
                object_id=str(backup.id),
            ).exists()
        )

    def test_non_tech_user_cannot_create_backup(self):
        self.client.force_authenticate(self.student)

        url = reverse("backup-run-backup")
        response = self.client.post(url, {"backup_type": "database"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_backup_restore_requires_tech_support(self):
        backup = Backup.objects.create(
            backup_type="database",
            status=Backup.Status.COMPLETED,
            created_by=self.tech,
        )

        self.client.force_authenticate(self.student)
        url = reverse("backup-restore", args=[backup.id])

        response = self.client.post(url, {"restore_type": "database"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
