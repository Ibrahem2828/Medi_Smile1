# apps/community/services.py
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit.services import log_audit_event
from apps.notifications.audit_bridge import notify_on_audit_event

from .models import Content, ContentLike, ContentComment


# ============================================================
# Content Services
# ============================================================

def create_content(*, author, data: dict) -> Content:
    if author.role.name == Role.PATIENT:
        raise PermissionDenied("Patients cannot create community content.")

    content = Content.objects.create(
        author=author,
        university=getattr(author, "university", None),
        **data,
    )

    # Auto-approved content (Supervisor / Admin / Tech)
    if content.status == Content.Status.APPROVED:
        log_audit_event(
            user=author,
            university=content.university,
            action="community.content.published",
            description="Community content published",
            content_object=content,
        )

    return content


def approve_content(*, moderator, content: Content) -> Content:
    if moderator.role.name not in {
        Role.SUPERVISOR,
        Role.UNIVERSITY_ADMIN,
        Role.TECH_SUPPORT,
    }:
        raise PermissionDenied("You are not allowed to approve content.")

    content.status = Content.Status.APPROVED
    content.approved_by = moderator
    content.approved_at = timezone.now()
    content.rejection_reason = ""
    content.save()

    log_audit_event(
        user=moderator,
        university=content.university,
        action="community.content.approved",
        description="Community content approved",
        content_object=content,
        metadata={"author_id": str(content.author_id)},
    )

    # Notifications (student author)
    notify_on_audit_event(
        action="community.content.approved",
        context={
            "author": content.author,
            "content_id": content.id,
            "content_object": content,
        },
    )

    return content


def reject_content(*, moderator, content: Content, reason: str) -> Content:
    if moderator.role.name not in {
        Role.SUPERVISOR,
        Role.UNIVERSITY_ADMIN,
        Role.TECH_SUPPORT,
    }:
        raise PermissionDenied("You are not allowed to reject content.")

    content.status = Content.Status.REJECTED
    content.rejection_reason = reason
    content.approved_by = moderator
    content.approved_at = timezone.now()
    content.save()

    log_audit_event(
        user=moderator,
        university=content.university,
        action="community.content.rejected",
        description="Community content rejected",
        content_object=content,
        metadata={"reason": reason, "author_id": str(content.author_id)},
    )

    # Notifications (student author)
    notify_on_audit_event(
        action="community.content.rejected",
        context={
            "author": content.author,
            "content_id": content.id,
            "content_object": content,
            "reason": reason,
        },
    )

    return content


# ============================================================
# Interaction Services
# ============================================================

def toggle_like(*, user, content: Content) -> bool:
    like, created = ContentLike.objects.get_or_create(
        user=user,
        content=content,
    )

    if not created:
        like.delete()
        return False

    log_audit_event(
        user=user,
        university=content.university,
        action="community.content.liked",
        description="Community content liked",
        content_object=content,
        metadata={"author_id": str(content.author_id)},
    )

    return True


def add_comment(*, user, content: Content, text: str) -> ContentComment:
    if user.role.name == Role.PATIENT:
        raise PermissionDenied("Patients cannot comment on content.")

    comment = ContentComment.objects.create(
        user=user,
        content=content,
        text=text,
        is_approved=True,
    )

    log_audit_event(
        user=user,
        university=content.university,
        action="community.content.commented",
        description="Community content commented",
        content_object=content,
        metadata={"comment_id": str(comment.id)},
    )

    return comment
