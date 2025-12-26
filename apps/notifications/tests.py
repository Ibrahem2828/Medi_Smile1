# apps/notifications/tests.py
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from apps.accounts.models import User, Role
from .models import Notification


class NotificationAPITestCase(APITestCase):
    def setUp(self):
        self.patient_role = Role.objects.get(name=Role.PATIENT)
        self.student_role = Role.objects.get(name=Role.STUDENT)

        self.patient = User.objects.create_user(
            username="patient1",
            password="pass1234",
            role=self.patient_role,
        )

        self.student = User.objects.create_user(
            username="student1",
            password="pass1234",
            role=self.student_role,
        )

        self.notification = Notification.objects.create(
            sender=self.student,
            recipient=self.patient,
            notification_type="test",
            title="Test Notification",
            message="This is a test notification",
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_list_notifications_for_recipient(self):
        self.authenticate(self.patient)

        url = reverse("notifications:notification-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_cannot_view_others_notifications(self):
        self.authenticate(self.student)

        url = reverse(
            "notifications:notification-detail",
            args=[self.notification.id],
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_mark_notification_as_read(self):
        self.authenticate(self.patient)

        url = reverse(
            "notifications:notification-detail",
            args=[self.notification.id],
        )

        response = self.client.patch(
            url,
            {"is_read": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
