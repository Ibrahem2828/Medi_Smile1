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
        cls.university_admin_role = Role.objects.create(name=Role.UNIVERSITY_ADMIN)

        # University
        cls.university = University.objects.create(
            name="Messaging University",
            city="City",
            country="Country",
        )

        # Users
        cls.patient = cls._create_user_with_role(
            email="patient@msg.test",
            username="patient_msg",
            password="Patient123!",
            role=cls.patient_role,
        )

        cls.student = cls._create_user_with_role(
            email="student@msg.test",
            username="student_msg",
            password="Student123!",
            role=cls.student_role,
            university=cls.university,
        )

        cls.supervisor = cls._create_user_with_role(
            email="supervisor@msg.test",
            username="supervisor_msg",
            password="Supervisor123!",
            role=cls.supervisor_role,
            university=cls.university,
        )

        cls.university_admin = cls._create_user_with_role(
            email="admin@msg.test",
            username="admin_msg",
            password="Admin123!",
            role=cls.university_admin_role,
            university=cls.university,
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
            participant_patient=cls.patient,
            participant_student=cls.student,
        )

    @classmethod
    def _create_user_with_role(cls, *, email, username, password, role, university=None):
        user = User(
            email=email,
            username=username,
            role=role,
        )
        if university:
            user._desired_university_id = university.id
        user.set_password(password)
        user.save()

        # Ensure profile university linkage is set when required
        if university and role.name == Role.STUDENT:
            profile = user.studentprofile_profile
            profile.university = university
            profile.save(update_fields=["university"])
        elif university and role.name == Role.SUPERVISOR:
            profile = user.supervisorprofile_profile
            profile.university = university
            profile.save(update_fields=["university"])
        elif university and role.name == Role.UNIVERSITY_ADMIN:
            profile = user.universityadminprofile_profile
            profile.university = university
            profile.save(update_fields=["university"])
        return user


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

    def test_supervisor_can_view_room(self):
        self.client.login(email="supervisor@msg.test", password="Supervisor123!")
        url = reverse(
            "messaging-room-detail",
            kwargs={"pk": self.room.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_university_admin_can_read_only(self):
        self.client.login(email="admin@msg.test", password="Admin123!")
        url = reverse(
            "messaging-room-detail",
            kwargs={"pk": self.room.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Admin cannot send messages (should be forbidden)
        msg_url = reverse(
            "message-list-create",
            kwargs={"room_id": self.room.id},
        )
        response = self.client.post(msg_url, {"content": "Admin attempt"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_send_when_case_closed(self):
        self.case.status = Case.Status.IN_PROGRESS
        self.case.save(update_fields=["status"])
        self.case.status = Case.Status.COMPLETED
        self.case.save(update_fields=["status"])

        self.client.login(email="student@msg.test", password="Student123!")
        url = reverse(
            "message-list-create",
            kwargs={"room_id": self.room.id},
        )
        response = self.client.post(url, {"content": "Late message"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_room_requests_not_creating_new(self):
        self.client.login(email="patient@msg.test", password="Patient123!")
        url = reverse("messaging-room-create")
        payload = {"case": str(self.case.id)}

        first = self.client.post(url, payload)
        second = self.client.post(url, payload)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Room.objects.filter(case=self.case).count(), 1)
