# apps/appointments/tests.py
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.universities.models import University
from apps.cases.models import Case
from apps.appointments.models import Appointment


class AppointmentsBaseTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Roles
        cls.patient_role = Role.objects.create(name=Role.PATIENT)
        cls.student_role = Role.objects.create(name=Role.STUDENT)
        cls.supervisor_role = Role.objects.create(name=Role.SUPERVISOR)
        cls.admin_role = Role.objects.create(name=Role.UNIVERSITY_ADMIN)
        cls.tech_role = Role.objects.create(name=Role.TECH_SUPPORT)

        # University
        cls.university = University.objects.create(
            name="Dental University",
            city="City",
            country="Country",
        )

        # Users
        cls.patient = User.objects.create_user(
            email="patient@appt.test",
            username="patient_appt",
            password="Patient123!",
            role=cls.patient_role,
        )

        cls.student = User.objects.create_user(
            email="student@appt.test",
            username="student_appt",
            password="Student123!",
            role=cls.student_role,
        )

        cls.supervisor = User.objects.create_user(
            email="supervisor@appt.test",
            username="supervisor_appt",
            password="Supervisor123!",
            role=cls.supervisor_role,
        )

        cls.admin = User.objects.create_user(
            email="admin@appt.test",
            username="admin_appt",
            password="Admin123!",
            role=cls.admin_role,
        )
        cls.admin.universityadminprofile_profile.university = cls.university
        cls.admin.universityadminprofile_profile.save()

        cls.tech = User.objects.create_user(
            email="tech@appt.test",
            username="tech_appt",
            password="Tech123!",
            role=cls.tech_role,
            is_staff=True,
        )

        # Assigned case
        cls.case = Case.objects.create(
            title="Appointment Case",
            description="Case for appointment testing",
            patient=cls.patient,
            student=cls.student,
            supervisor=cls.supervisor,
            university=cls.university,
            status=Case.Status.ASSIGNED,
        )


# ============================================================
# Appointment Creation Tests
# ============================================================
class AppointmentCreationTests(AppointmentsBaseTestCase):
    def test_student_can_create_appointment(self):
        self.client.login(email="student@appt.test", password="Student123!")

        url = reverse("appointment-list-create")
        response = self.client.post(
            url,
            {
                "case_id": str(self.case.id),
                "scheduled_at": timezone.now() + timezone.timedelta(days=1),
                "notes": "Initial appointment",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_patient_cannot_create_appointment(self):
        self.client.login(email="patient@appt.test", password="Patient123!")

        url = reverse("appointment-list-create")
        response = self.client.post(
            url,
            {
                "case_id": str(self.case.id),
                "scheduled_at": timezone.now() + timezone.timedelta(days=1),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================
# Appointment Visibility Tests
# ============================================================
class AppointmentVisibilityTests(AppointmentsBaseTestCase):
    def setUp(self):
        self.appointment = Appointment.objects.create(
            case=self.case,
            patient=self.patient,
            student=self.student,
            supervisor=self.supervisor,
            created_by=self.student,
            scheduled_at=timezone.now() + timezone.timedelta(days=2),
        )

    def test_patient_can_view_own_appointment(self):
        self.client.login(email="patient@appt.test", password="Patient123!")

        url = reverse("appointment-detail", args=[self.appointment.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_patient_cannot_view_appointment(self):
        other_patient = User.objects.create_user(
            email="other@appt.test",
            username="other_patient",
            password="Other123!",
            role=self.patient_role,
        )

        self.client.login(email="other@appt.test", password="Other123!")
        url = reverse("appointment-detail", args=[self.appointment.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================
# University & IT Scope Tests
# ============================================================
class AppointmentScopeTests(AppointmentsBaseTestCase):
    def setUp(self):
        Appointment.objects.create(
            case=self.case,
            patient=self.patient,
            student=self.student,
            supervisor=self.supervisor,
            created_by=self.student,
            scheduled_at=timezone.now() + timezone.timedelta(days=3),
        )

    def test_university_admin_sees_only_university_appointments(self):
        self.client.login(email="admin@appt.test", password="Admin123!")

        url = reverse("appointment-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_tech_support_sees_all_appointments(self):
        self.client.login(email="tech@appt.test", password="Tech123!")

        url = reverse("appointment-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
