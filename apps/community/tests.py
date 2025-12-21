from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Content, ContentLike, ContentComment
from apps.universities.models import University

User = get_user_model()


class CommunityContentTestCase(TestCase):
    """
    Tests for Community Content logic and permissions.
    """

    def setUp(self):
        self.university = University.objects.create(
            name="Test University"
        )

        self.student = User.objects.create_user(
            email="student@test.com",
            username="student",
            password="pass123",
            role="student"
        )

        self.supervisor = User.objects.create_user(
            email="supervisor@test.com",
            username="supervisor",
            password="pass123",
            role="supervisor"
        )

        self.patient = User.objects.create_user(
            email="patient@test.com",
            username="patient",
            password="pass123",
            role="patient"
        )

    def test_student_content_requires_approval(self):
        """
        Student-created content must be pending approval.
        """
        content = Content.objects.create(
            title="Student Post",
            description="Educational content",
            content_type="article",
            category="educational",
            author=self.student,
            university=self.university,
        )

        self.assertEqual(content.status, "pending")

    def test_supervisor_content_auto_approved(self):
        """
        Supervisor-created content is auto-approved.
        """
        content = Content.objects.create(
            title="Supervisor Post",
            description="Medical article",
            content_type="article",
            category="medical",
            author=self.supervisor,
            university=self.university,
            status="approved",
        )

        self.assertEqual(content.status, "approved")

    def test_like_content_once(self):
        """
        User can like content only once.
        """
        content = Content.objects.create(
            title="Like Test",
            description="Test",
            content_type="article",
            category="general",
            author=self.supervisor,
            status="approved",
        )

        like1 = ContentLike.objects.create(
            content=content,
            user=self.student
        )

        self.assertEqual(ContentLike.objects.count(), 1)

        # Duplicate like should not create new one
        with self.assertRaises(Exception):
            ContentLike.objects.create(
                content=content,
                user=self.student
            )

    def test_comment_creation(self):
        """
        Authenticated users can comment on approved content.
        """
        content = Content.objects.create(
            title="Comment Test",
            description="Test",
            content_type="article",
            category="general",
            author=self.supervisor,
            status="approved",
        )

        comment = ContentComment.objects.create(
            content=content,
            user=self.student,
            text="Great article!"
        )

        self.assertEqual(comment.content, content)
        self.assertEqual(comment.user, self.student)
        self.assertTrue(comment.is_approved)


class CommunityVisibilityTestCase(TestCase):
    """
    Tests for content visibility rules.
    """

    def setUp(self):
        self.student = User.objects.create_user(
            email="student2@test.com",
            username="student2",
            password="pass123",
            role="student"
        )

    def test_public_content_visible(self):
        content = Content.objects.create(
            title="Public Content",
            description="Visible",
            content_type="article",
            category="general",
            author=self.student,
            status="approved",
            is_public=True,
        )

        self.assertTrue(content.is_public)

    def test_private_content_hidden(self):
        content = Content.objects.create(
            title="Private Content",
            description="Hidden",
            content_type="article",
            category="general",
            author=self.student,
            status="approved",
            is_public=False,
        )

        self.assertFalse(content.is_public)
