# apps/messaging/tests.py
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.universities.models import University
from apps.cases.models import Case
from apps.messaging.models import Room, Message


class MessagingBaseTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Roles
        cls.patient_role = Role.objects.create(name=Role.PATIENT)
        cls.student_role = Role.objects.create(name=Role.STUDENT)
        cls.supervisor_role = Role.objects.create(name=Role.SUPERVISOR)

        # University
        cls.university = University.objects.create(
            name="Messaging University",
            city="City",
            country="Country",
        )

        # Users
        cls.patient = User.objects.create_user(
            email="patient@msg.test",
            username="patient_msg",
            password="Patient123!",
            role=cls.patient_role,
        )

        cls.student = User.objects.create_user(
            email="student@msg.test",
            username="student_msg",
            password="Student123!",
            role=cls.student_role,
        )

        cls.supervisor = User.objects.create_user(
            email="supervisor@msg.test",
            username="supervisor_msg",
            password="Supervisor123!",
            role=cls.supervisor_role,
        )

        # Case
        cls.case = Case.objects.create(
            title="Messaging Case",
            description="Case for messaging tests",
            patient=cls.patient,
            student=cls.student,
            supervisor=cls.supervisor,
            university=cls.university,
            status=Case.Status.ASSIGNED,
        )

        cls.room = Room.objects.create(
            case=cls.case,
            participant1=cls.patient,
            participant2=cls.student,
        )


class MessageTests(MessagingBaseTestCase):
    def test_participant_can_send_message(self):
        self.client.login(email="student@msg.test", password="Student123!")

        url = reverse(
            "message-list-create",
            kwargs={"room_id": self.room.id},
        )

        response = self.client.post(
            url,
            {"content": "Hello patient"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.count(), 1)

    def test_non_participant_cannot_send_message(self):
        other_user = User.objects.create_user(
            email="other@msg.test",
            username="other_msg",
            password="Other123!",
            role=self.patient_role,
        )

        self.client.login(email="other@msg.test", password="Other123!")

        url = reverse(
            "message-list-create",
            kwargs={"room_id": self.room.id},
        )

        response = self.client.post(
            url,
            {"content": "Hack attempt"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
