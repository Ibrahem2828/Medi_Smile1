# apps/attachments/tests.py
from base64 import b64decode
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.universities.models import University
from apps.cases.models import Case
from apps.appointments.models import Appointment
from apps.attachments.models import Attachment


class AttachmentsBaseTestCase(APITestCase):
    @classmethod
    def _create_user_with_university(cls, *, email, username, password, role, university):
        user = User(email=email, username=username, role=role)
        user._desired_university_id = university.id
        user.set_password(password)
        user.save()
        return user

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
            email="patient@attach.test",
            username="patient_attach",
            password="Patient123!",
            role=cls.patient_role,
        )

        cls.student = cls._create_user_with_university(
            email="student@attach.test",
            username="student_attach",
            password="Student123!",
            role=cls.student_role,
            university=cls.university,
        )

        cls.supervisor = cls._create_user_with_university(
            email="supervisor@attach.test",
            username="supervisor_attach",
            password="Supervisor123!",
            role=cls.supervisor_role,
            university=cls.university,
        )

        cls.admin = cls._create_user_with_university(
            email="admin@attach.test",
            username="admin_attach",
            password="Admin123!",
            role=cls.admin_role,
            university=cls.university,
        )
        cls.admin.universityadminprofile_profile.university = cls.university
        cls.admin.universityadminprofile_profile.save()

        cls.tech = User.objects.create_user(
            email="tech@attach.test",
            username="tech_attach",
            password="Tech123!",
            role=cls.tech_role,
            is_staff=True,
        )

        # Case
        cls.case = Case.objects.create(
            title="Attachment Case",
            description="Case for attachment tests",
            patient=cls.patient,
            student=cls.student,
            supervisor=cls.supervisor,
            university=cls.university,
            status=Case.Status.ASSIGNED,
        )

        # Appointment
        cls.appointment = Appointment.objects.create(
            case=cls.case,
            patient=cls.patient,
            student=cls.student,
            supervisor=cls.supervisor,
            created_by=cls.student,
            scheduled_at=timezone.now() + timezone.timedelta(days=1),
        )


# ============================================================
# Upload Tests
# ============================================================
class AttachmentUploadTests(AttachmentsBaseTestCase):
    def test_student_can_upload_attachment(self):
        self.client.login(email="student@attach.test", password="Student123!")

        file = SimpleUploadedFile(
            "before.png",
            b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2"
                "FzhVAAAAAElFTkSuQmCC"
            ),
            content_type="image/png",
        )

        url = reverse("attachment-list-create")
        response = self.client.post(
            url,
            {
                "appointment_id": str(self.appointment.id),
                "file": file,
                "attachment_type": Attachment.AttachmentType.BEFORE_IMAGE,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Attachment.objects.count(), 1)

    def test_patient_cannot_upload_attachment(self):
        self.client.login(email="patient@attach.test", password="Patient123!")

        file = SimpleUploadedFile(
            "test.jpg",
            b"file_content",
            content_type="image/jpeg",
        )

        url = reverse("attachment-list-create")
        response = self.client.post(
            url,
            {
                "appointment_id": str(self.appointment.id),
                "file": file,
                "attachment_type": Attachment.AttachmentType.BEFORE_IMAGE,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================
# Visibility Tests
# ============================================================
class AttachmentVisibilityTests(AttachmentsBaseTestCase):
    def setUp(self):
        self.attachment = Attachment.objects.create(
            case=self.case,
            appointment=self.appointment,
            uploaded_by=self.student,
            file="attachments/test.jpg",
            original_filename="test.jpg",
            file_size=100,
            mime_type="image/jpeg",
            attachment_type=Attachment.AttachmentType.BEFORE_IMAGE,
            file_category=Attachment.FileCategory.IMAGE,
            is_visible_to_patient=True,
        )

    def test_patient_can_view_visible_attachment(self):
        self.client.login(email="patient@attach.test", password="Patient123!")

        url = reverse("attachment-detail", args=[self.attachment.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patient_cannot_view_hidden_attachment(self):
        self.attachment.is_visible_to_patient = False
        self.attachment.save()

        self.client.login(email="patient@attach.test", password="Patient123!")

        url = reverse("attachment-detail", args=[self.attachment.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
