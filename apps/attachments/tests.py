# apps/attachments/tests.py

from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.attachments.models import Attachment
from apps.cases.models import Case


class AttachmentBaseTestCase(TestCase):
    """
    Base setup for attachment tests.
    """

    def setUp(self):
        self.client = APIClient()

        # -------------------------------
        # Users
        # -------------------------------
        self.patient = User.objects.create_user(
            email="patient@test.com",
            username="patient",
            password="pass1234",
            role="patient",
        )

        self.student = User.objects.create_user(
            email="student@test.com",
            username="student",
            password="pass1234",
            role="student",
        )

        self.supervisor = User.objects.create_user(
            email="supervisor@test.com",
            username="supervisor",
            password="pass1234",
            role="supervisor",
        )

        # -------------------------------
        # Case
        # -------------------------------
        self.case = Case.objects.create(
            title="Test Case",
            description="Dental case",
            patient=self.patient,
            student=self.student,
            supervisor=self.supervisor,
            status=Case.Status.ASSIGNED,
        )

        # -------------------------------
        # File
        # -------------------------------
        self.image_file = SimpleUploadedFile(
            "before.jpg",
            b"fake-image-content",
            content_type="image/jpeg",
        )


class AttachmentUploadTest(AttachmentBaseTestCase):
    """
    Test uploading attachments.
    """

    def test_student_can_upload_case_attachment(self):
        """Student can upload attachment for assigned case."""
        self.client.force_authenticate(self.student)

        response = self.client.post(
            reverse("attachment-list"),
            {
                "file": self.image_file,
                "case_id": self.case.id,
                "is_public": False,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Attachment.objects.count(), 1)

        attachment = Attachment.objects.first()
        self.assertEqual(attachment.uploaded_by, self.student)
        self.assertEqual(attachment.case_id, self.case.id)
        self.assertEqual(attachment.file_type, "image")

    def test_patient_can_upload_own_attachment(self):
        """Patient can upload attachment for own case."""
        self.client.force_authenticate(self.patient)

        response = self.client.post(
            reverse("attachment-list"),
            {
                "file": self.image_file,
                "case_id": self.case.id,
                "is_public": False,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Attachment.objects.first().uploaded_by, self.patient)


class AttachmentAccessTest(AttachmentBaseTestCase):
    """
    Test access control to attachments.
    """

    def setUp(self):
        super().setUp()

        self.attachment = Attachment.objects.create(
            file=self.image_file,
            original_filename="before.jpg",
            file_type="image",
            file_size=123,
            mime_type="image/jpeg",
            case_id=self.case.id,
            uploaded_by=self.student,
            is_public=False,
        )

    def test_patient_can_view_own_case_attachment(self):
        """Patient can view attachment related to own case."""
        self.client.force_authenticate(self.patient)

        response = self.client.get(
            reverse("attachment-detail", args=[self.attachment.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_patient_cannot_view_attachment(self):
        """Other patients cannot access attachment."""
        other_patient = User.objects.create_user(
            email="other@test.com",
            username="other",
            password="pass1234",
            role="patient",
        )

        self.client.force_authenticate(other_patient)

        response = self.client.get(
            reverse("attachment-detail", args=[self.attachment.id])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_supervisor_can_view_case_attachment(self):
        """Supervisor can view attachment for supervised case."""
        self.client.force_authenticate(self.supervisor)

        response = self.client.get(
            reverse("attachment-detail", args=[self.attachment.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AttachmentDownloadTest(AttachmentBaseTestCase):
    """
    Test downloading attachments.
    """

    def setUp(self):
        super().setUp()

        self.attachment = Attachment.objects.create(
            file=self.image_file,
            original_filename="before.jpg",
            file_type="image",
            file_size=123,
            mime_type="image/jpeg",
            case_id=self.case.id,
            uploaded_by=self.student,
            is_public=False,
        )

    def test_student_can_download_attachment(self):
        """Student can download attachment."""
        self.client.force_authenticate(self.student)

        response = self.client.get(
            reverse("download-attachment", args=[self.attachment.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Content-Disposition", response.headers)

    def test_patient_cannot_download_unrelated_attachment(self):
        """Patient cannot download attachment from other case."""
        other_patient = User.objects.create_user(
            email="other@test.com",
            username="other",
            password="pass1234",
            role="patient",
        )

        self.client.force_authenticate(other_patient)

        response = self.client.get(
            reverse("download-attachment", args=[self.attachment.id])
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
