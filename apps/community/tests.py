# apps/community/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role
from apps.universities.models import University
from apps.evaluations.models import Evaluation, EvaluationStatus
from apps.notifications.models import Notification
from apps.audit.models import AuditLog

from .models import Content


class CommunityAPITests(APITestCase):

    def setUp(self):
        self.university = University.objects.create(name="Test University")

        self.student = User.objects.create_user(
            username="student",
            password="pass",
            role=Role.objects.get(name=Role.STUDENT),
            university=self.university,
        )

        self.supervisor = User.objects.create_user(
            username="supervisor",
            password="pass",
            role=Role.objects.get(name=Role.SUPERVISOR),
            university=self.university,
        )

        self.patient = User.objects.create_user(
            username="patient",
            password="pass",
            role=Role.objects.get(name=Role.PATIENT),
        )

    # ---------------------------------------------------------
    # Public Rating
    # ---------------------------------------------------------

    def test_student_rating_endpoint(self):
        Evaluation.objects.create(
            university=self.university,
            evaluator=self.supervisor,
            student=self.student,
            target_type="case",
            score=90,
            status=EvaluationStatus.FINAL,
        )

        self.client.force_authenticate(self.patient)
        url = reverse("community:student-public-rating", args=[self.student.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["stars"], 5)

    # ---------------------------------------------------------
    # Content Flow
    # ---------------------------------------------------------

    def test_student_content_is_pending_by_default(self):
        self.client.force_authenticate(self.student)
        url = reverse("community:content-list")

        res = self.client.post(
            url,
            {
                "title": "Post",
                "description": "Desc",
                "content_type": "link",
                "category": "general",
                "url": "https://example.com",
            },
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        content = Content.objects.first()
        self.assertEqual(content.status, Content.Status.PENDING)

    # ---------------------------------------------------------
    # Audit + Notification
    # ---------------------------------------------------------

    def test_approve_content_creates_audit_and_notification(self):
        content = Content.objects.create(
            author=self.student,
            university=self.university,
            title="Pending Post",
            status=Content.Status.PENDING,
        )

        self.client.force_authenticate(self.supervisor)
        url = reverse("community:content-approve", args=[content.id])
        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Audit log
        self.assertTrue(
            AuditLog.objects.filter(
                action="community.content.approved",
                user=self.supervisor,
            ).exists()
        )

        # Notification to student
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                notification_type="community_content_approved",
            ).exists()
        )

    def test_reject_content_creates_audit_and_notification(self):
        content = Content.objects.create(
            author=self.student,
            university=self.university,
            title="Pending Post",
            status=Content.Status.PENDING,
        )

        self.client.force_authenticate(self.supervisor)
        url = reverse("community:content-reject", args=[content.id])
        res = self.client.post(url, {"reason": "Not suitable"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Audit log
        self.assertTrue(
            AuditLog.objects.filter(
                action="community.content.rejected",
                user=self.supervisor,
            ).exists()
        )

        # Notification to student
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                notification_type="community_content_rejected",
            ).exists()
        )
