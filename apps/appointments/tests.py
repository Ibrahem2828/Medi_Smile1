# apps/appointments/tests.py

from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from django.test import TestCase

from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.cases.models import Case
from .models import Appointment


class AppointmentBaseTestCase(TestCase):
    """
    Base setup for appointment-related tests.
    """

    def setUp(self):
        self.client = APIClient()

        # -------------------------------------------------
        # Users
        # -------------------------------------------------
        self.patient = User.objects.create_user(
            email="patient@test.com",
            password="pass1234",
            role="patient",
        )

        self.student = User.objects.create_user(
            email="student@test.com",
            password="pass1234",
            role="student",
        )

        self.supervisor = User.objects.create_user(
            email="supervisor@test.com",
            password="pass1234",
            role="supervisor",
        )

        self.university_admin = User.objects.create_user(
            email="admin@test.com",
            password="pass1234",
            role="university_admin",
        )

        # -------------------------------------------------
        # Case (assigned)
        # -------------------------------------------------
        self.case = Case.objects.create(
            title="Root Canal",
            description="Deep caries",
            patient=self.patient,
            student=self.student,
            supervisor=self.supervisor,
            status=Case.Status.ASSIGNED,
        )

        self.appointment_date = timezone.now() + timedelta(days=1)


class AppointmentCreateTests(AppointmentBaseTestCase):
    """
    Tests for appointment creation.
    """

    def test_student_can_create_appointment(self):
        self.client.force_authenticate(user=self.student)

        url = reverse("appointments:appointment-list")
        payload = {
            "case_id": str(self.case.id),
            "appointment_date": self.appointment_date.isoformat(),
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Appointment.objects.count(), 1)

        appointment = Appointment.objects.first()
        self.assertEqual(appointment.patient, self.patient)
        self.assertEqual(appointment.created_by, self.student)
        self.assertEqual(appointment.status, Appointment.Status.SCHEDULED)

    def test_patient_cannot_create_appointment(self):
        self.client.force_authenticate(user=self.patient)

        url = reverse("appointments:appointment-list")
        payload = {
            "case_id": str(self.case.id),
            "appointment_date": self.appointment_date.isoformat(),
        }

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AppointmentVisibilityTests(AppointmentBaseTestCase):
    """
    Tests for appointment listing visibility.
    """

    def setUp(self):
        super().setUp()

        self.appointment = Appointment.objects.create(
            patient=self.patient,
            created_by=self.student,
            case=self.case,
            appointment_date=self.appointment_date,
        )

    def test_patient_sees_own_appointment(self):
        self.client.force_authenticate(user=self.patient)

        url = reverse("appointments:appointment-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_student_sees_own_created_appointment(self):
        self.client.force_authenticate(user=self.student)

        url = reverse("appointments:appointment-list")
        response = self.client.get(url)

        self.assertEqual(len(response.data), 1)

    def test_supervisor_sees_case_appointments(self):
        self.client.force_authenticate(user=self.supervisor)

        url = reverse("appointments:appointment-list")
        response = self.client.get(url)

        self.assertEqual(len(response.data), 1)


class AppointmentStatusFlowTests(AppointmentBaseTestCase):
    """
    Tests for appointment status transitions.
    """

    def setUp(self):
        super().setUp()

        self.appointment = Appointment.objects.create(
            patient=self.patient,
            created_by=self.student,
            case=self.case,
            appointment_date=self.appointment_date,
        )

    def test_patient_confirms_appointment(self):
        self.client.force_authenticate(user=self.patient)

        url = reverse(
            "appointments:appointment-confirm",
            args=[self.appointment.id],
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.CONFIRMED)

    def test_student_starts_appointment(self):
        self.appointment.status = Appointment.Status.CONFIRMED
        self.appointment.save()

        self.client.force_authenticate(user=self.student)

        url = reverse(
            "appointments:appointment-start",
            args=[self.appointment.id],
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.IN_PROGRESS)

    def test_student_completes_appointment(self):
        self.appointment.status = Appointment.Status.IN_PROGRESS
        self.appointment.save()

        self.client.force_authenticate(user=self.student)

        url = reverse(
            "appointments:appointment-complete",
            args=[self.appointment.id],
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)

    def test_patient_cannot_complete_appointment(self):
        self.appointment.status = Appointment.Status.CONFIRMED
        self.appointment.save()

        self.client.force_authenticate(user=self.patient)

        url = reverse(
            "appointments:appointment-complete",
            args=[self.appointment.id],
        )

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AppointmentCancellationTests(AppointmentBaseTestCase):
    """
    Tests for appointment cancellation.
    """

    def setUp(self):
        super().setUp()

        self.appointment = Appointment.objects.create(
            patient=self.patient,
            created_by=self.student,
            case=self.case,
            appointment_date=self.appointment_date,
            status=Appointment.Status.CONFIRMED,
        )

    def test_patient_can_cancel_appointment(self):
        self.client.force_authenticate(user=self.patient)

        url = reverse(
            "appointments:appointment-cancel",
            args=[self.appointment.id],
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.CANCELLED)

    def test_student_can_mark_no_show(self):
        self.client.force_authenticate(user=self.student)

        url = reverse(
            "appointments:appointment-no-show",
            args=[self.appointment.id],
        )

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.NO_SHOW)
