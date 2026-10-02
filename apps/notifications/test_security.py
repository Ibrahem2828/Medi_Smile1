# apps/notifications/test_security.py
"""Notification anti-spoofing: senders may only notify related users, as themselves."""
from django.urls import reverse
from rest_framework import status

from apps.cases.models import Case
from apps.notifications.models import Notification
from medismile.testing import TwoUniversitiesTestCase


class NotificationSpoofingTests(TwoUniversitiesTestCase):
    def setUp(self):
        self.case = Case.objects.create(
            patient=self.patient,
            title="Case",
            description="d",
            university=self.uni_a,
            student=self.student_a,
            supervisor=self.supervisor_a,
            status=Case.Status.NEW,
        )
        self.url = reverse("notifications:notification-create")

    def payload(self, recipient, **extra):
        body = {
            "notification_type": "system_alert",
            "recipient_id": str(recipient.id),
            "target_type": "case",
            "target_id": str(self.case.id),
            "title": "Hello",
            "message": "Message",
        }
        body.update(extra)
        return body

    def test_case_participant_can_notify_other_participant(self):
        self.login(self.student_a)
        response = self.client.post(self.url, self.payload(self.patient), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        notification = Notification.objects.get()
        self.assertEqual(notification.sender_id, self.student_a.id)
        self.assertEqual(response.data["id"], str(notification.id))
        self.assertEqual(response.data["sender"]["id"], str(self.student_a.id))

    def test_cannot_notify_unrelated_user_through_case(self):
        self.login(self.student_a)
        response = self.client.post(self.url, self.payload(self.other_patient), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Notification.objects.exists())

    def test_outsider_cannot_notify_case_participants(self):
        self.login(self.student_b)
        response = self.client.post(self.url, self.payload(self.patient), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_impersonate_sender(self):
        self.login(self.student_a)
        response = self.client.post(
            self.url, self.payload(self.patient, sender_id=str(self.supervisor_a.id)), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Notification.objects.exists())

    def test_staff_cannot_notify_other_university_users(self):
        self.login(self.supervisor_b)
        response = self.client.post(
            self.url,
            self.payload(self.student_a, target_type="user", target_id=str(self.student_a.id)),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_can_notify_same_university_users(self):
        self.login(self.supervisor_a)
        response = self.client.post(
            self.url,
            self.payload(self.student_a, target_type="user", target_id=str(self.student_a.id)),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_university_admin_can_notify_within_own_case(self):
        self.login(self.admin_a)
        response = self.client.post(self.url, self.payload(self.patient), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_tech_support_can_notify_anyone(self):
        self.login(self.tech)
        response = self.client.post(
            self.url,
            self.payload(self.other_patient, target_type="user", target_id=str(self.other_patient.id)),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
