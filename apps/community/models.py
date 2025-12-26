# apps/community/models.py
import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role


# ============================================================
# Community Content
# ============================================================

class Content(models.Model):
    """
    Educational / medical content inside MediSmile community.

    Rules:
    - Student: requires approval
    - Supervisor / University Admin / Tech Support: auto-approved
    - Patient: read-only (likes only)
    """

    # =========================
    # Enums
    # =========================

    class ContentType(models.TextChoices):
        ARTICLE = "article", _("Article")
        VIDEO = "video", _("Video")
        DOCUMENT = "document", _("Document")
        IMAGE = "image", _("Image")
        LINK = "link", _("External Link")

    class Category(models.TextChoices):
        MEDICAL = "medical", _("Medical")
        EDUCATIONAL = "educational", _("Educational")
        RESEARCH = "research", _("Research")
        NEWS = "news", _("News")
        GENERAL = "general", _("General")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending Approval")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    # =========================
    # Fields
    # =========================

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=200, verbose_name=_("Title"))
    description = models.TextField(verbose_name=_("Description"))

    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        verbose_name=_("Content Type"),
    )

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        verbose_name=_("Category"),
    )

    file = models.FileField(
        upload_to="community/content/",
        blank=True,
        null=True,
        verbose_name=_("Attached File"),
    )

    url = models.URLField(
        blank=True,
        null=True,
        verbose_name=_("External URL"),
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="community_content",
        verbose_name=_("Author"),
    )

    university = models.ForeignKey(
        "universities.University",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="community_content",
        verbose_name=_("University"),
    )

    tags = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_("Tags (comma separated)"),
    )

    # =========================
    # Moderation
    # =========================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Approval Status"),
    )

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_content",
        limit_choices_to={
            "role__name__in": [
                Role.SUPERVISOR,
                Role.UNIVERSITY_ADMIN,
                Role.TECH_SUPPORT,
            ]
        },
        verbose_name=_("Approved / Rejected By"),
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Approved At"),
    )

    rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Rejection Reason"),
    )

    # =========================
    # Visibility
    # =========================

    is_public = models.BooleanField(
        default=True,
        verbose_name=_("Publicly Visible"),
        help_text=_("If false, visible only inside university."),
    )

    is_featured = models.BooleanField(
        default=False,
        verbose_name=_("Featured Content"),
    )

    # =========================
    # Stats
    # =========================

    view_count = models.PositiveIntegerField(default=0, verbose_name=_("View Count"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    # =========================
    # Meta
    # =========================

    class Meta:
        db_table = "community_content"
        verbose_name = _("Community Content")
        verbose_name_plural = _("Community Content")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["author"]),
            models.Index(fields=["university"]),
        ]

    # =========================
    # Validation
    # =========================

    def clean(self):
        # File / URL validation
        if self.content_type == self.ContentType.LINK and not self.url:
            raise ValidationError(_("URL is required for link content."))

        if self.content_type != self.ContentType.LINK and not self.file:
            raise ValidationError(_("File is required for this content type."))

        # Patient cannot create content
        if self.author.role.name == Role.PATIENT:
            raise ValidationError(_("Patients are not allowed to create content."))

    # =========================
    # Save Logic
    # =========================

    def save(self, *args, **kwargs):
        """
        Auto-approval rules:
        - Student → Pending
        - Supervisor / University Admin / Tech → Approved
        """

        role_name = getattr(getattr(self.author, "role", None), "name", None)

        if role_name in {
            Role.SUPERVISOR,
            Role.UNIVERSITY_ADMIN,
            Role.TECH_SUPPORT,
        }:
            self.status = self.Status.APPROVED
            self.approved_at = self.approved_at or timezone.now()

        elif role_name == Role.STUDENT:
            if self.status == self.Status.APPROVED:
                raise ValidationError(_("Student content must be approved by a supervisor."))

            self.status = self.Status.PENDING

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
# ============================================================
# Content Like
# ============================================================

class ContentLike(models.Model):
    """
    Like interaction on community content.

    Rules:
    - Patient: allowed
    - Student / Supervisor / Admin: allowed
    - One like per user per content
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    content = models.ForeignKey(
        Content,
        on_delete=models.CASCADE,
        related_name="likes",
        verbose_name=_("Content"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="content_likes",
        verbose_name=_("User"),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "community_content_likes"
        verbose_name = _("Content Like")
        verbose_name_plural = _("Content Likes")
        constraints = [
            models.UniqueConstraint(
                fields=["content", "user"],
                name="unique_like_per_user_per_content",
            )
        ]

    def __str__(self):
        return f"{self.user} liked {self.content}"
# ============================================================
# Content Comment
# ============================================================

class ContentComment(models.Model):
    """
    Comment on community content.

    Rules:
    - Patient: NOT allowed
    - Student / Supervisor / Admin: allowed
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    content = models.ForeignKey(
        Content,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("Content"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="content_comments",
        verbose_name=_("User"),
    )

    text = models.TextField(verbose_name=_("Comment"))

    is_approved = models.BooleanField(
        default=True,
        verbose_name=_("Approved"),
        help_text=_("Future moderation support."),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "community_content_comments"
        verbose_name = _("Content Comment")
        verbose_name_plural = _("Content Comments")
        ordering = ["created_at"]

    def clean(self):
        if self.user.role.name == Role.PATIENT:
            raise ValidationError(_("Patients are not allowed to comment."))

    def __str__(self):
        return f"Comment by {self.user} on {self.content}"
