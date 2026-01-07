# apps/community/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, Role, StudentProfile, SupervisorProfile
from apps.universities.models import University
from apps.evaluations.models import Evaluation, EvaluationStatus
from apps.notifications.models import Notification
from apps.audit.models import AuditLog

from .models import Content


class CommunityAPITests(APITestCase):

    def setUp(self):
        self.university = University.objects.create(name="Test University")

        student_role, _ = Role.objects.get_or_create(name=Role.STUDENT)
        supervisor_role, _ = Role.objects.get_or_create(name=Role.SUPERVISOR)
        patient_role, _ = Role.objects.get_or_create(name=Role.PATIENT)

        self.student = User.objects.create_user(
            username="student",
            password="pass",
            role=student_role,
        )
        StudentProfile.objects.create(user=self.student, university=self.university)

        self.patient = User.objects.create_user(
            username="patient",
            password="pass",
            role=patient_role,
        )

        self.supervisor = User.objects.create_user(
            username="supervisor",
            password="pass",
            role=supervisor_role,
        )
        SupervisorProfile.objects.create(user=self.supervisor, university=self.university)

    # ---------------------------------------------------------
    # Public Rating
    # ---------------------------------------------------------

    def test_student_rating_endpoint(self):
        Evaluation.objects.create(
            university=self.university,
            evaluator=self.supervisor,
            evaluator_role=Role.SUPERVISOR,
            student=self.student,
            target_type="student",
            target_id=self.student.id,
            score=90,
            final_score=90,
            status=EvaluationStatus.FINALIZED,
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
        url = reverse("community:posts-list")

        res = self.client.post(
            url,
            {
                "title": "Post",
                "content": "Educational text",
                "content_type": "text",
                "category": "general",
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
            description="Pending content",
            content_type=Content.ContentType.TEXT,
            category=Content.Category.GENERAL,
            status=Content.Status.PENDING,
        )

        self.client.force_authenticate(self.supervisor)
        url = reverse("community:posts-approve", args=[content.id])
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
            description="Pending content",
            content_type=Content.ContentType.TEXT,
            category=Content.Category.GENERAL,
            status=Content.Status.PENDING,
        )

        self.client.force_authenticate(self.supervisor)
        url = reverse("community:posts-reject", args=[content.id])
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
