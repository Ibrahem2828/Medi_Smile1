from django.test import TestCase
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from apps.notifications.models import Notification
from apps.appointments.models import Appointment
from apps.cases.models import Case

User = get_user_model()


class NotificationModelTest(TestCase):
    """
    Basic tests for Notification model.
    """

    def setUp(self):
        self.sender = User.objects.create_user(
            email="student@test.com",
            username="student1",
            password="testpass123",
            role="student",
        )

        self.recipient = User.objects.create_user(
            email="patient@test.com",
            username="patient1",
            password="testpass123",
            role="patient",
        )

        self.case = Case.objects.create(
            title="Test Case",
            description="Test case description",
            patient=self.recipient,
            status=Case.Status.ASSIGNED,
        )

        self.appointment = Appointment.objects.create(
            patient=self.recipient,
            created_by=self.sender,
            case=self.case,
            appointment_date="2030-01-01T10:00:00Z",
        )

    def test_create_notification(self):
        notification = Notification.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            notification_type="appointment_confirmed",
            appointment=self.appointment,
            title="Appointment Confirmed",
            message="Your appointment has been confirmed.",
            status="accepted",
        )

        self.assertEqual(notification.sender, self.sender)
        self.assertEqual(notification.recipient, self.recipient)
        self.assertEqual(notification.appointment, self.appointment)
        self.assertFalse(notification.is_read)

    def test_mark_notification_as_read(self):
        notification = Notification.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            notification_type="appointment_confirmed",
            appointment=self.appointment,
            title="Appointment Confirmed",
            message="Confirmed",
            status="accepted",
        )

        notification.is_read = True
        notification.save(update_fields=["is_read"])

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_notification_str(self):
        notification = Notification.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            notification_type="appointment_confirmed",
            title="Test Notification",
            message="Test message",
            status="accepted",
        )

        self.assertIn("Test Notification", str(notification))
