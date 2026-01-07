# apps/community/services.py
import logging
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.utils import timezone

from apps.accounts.models import Role
from apps.audit.services import log_audit_event
from apps.notifications.audit_bridge import notify_on_audit_event

from .models import Content, ContentLike, ContentComment, CommunityApprovalLog
from .selectors import _resolve_university_id

logger = logging.getLogger(__name__)


# ============================================================
# Content Services
# ============================================================

def create_content(*, author, data: dict) -> Content:
    role_name = getattr(getattr(author, "role", None), "name", None)
    if not role_name:
        raise PermissionDenied("User role is missing; contact admin.")
    if role_name not in {Role.STUDENT, Role.SUPERVISOR}:
        raise PermissionDenied("You are not allowed to create community posts.")

    university_id = _resolve_university_id(author)
    if not university_id:
        raise PermissionDenied("University is required to create community posts.")

    try:
        content = Content(
            author=author,
            university_id=university_id,
            **data,
        )
        content.full_clean()
        content.save()
    except DjangoValidationError as exc:
        detail = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc)
        logger.warning("Community content validation failed: %s", detail)
        raise PermissionDenied(detail)
    except Exception as exc:
        logger.exception("Community content create failed", exc_info=exc)
        raise PermissionDenied("Failed to create content.")

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
    role_name = getattr(getattr(moderator, "role", None), "name", None)
    if role_name != Role.SUPERVISOR:
        raise PermissionDenied("You are not allowed to approve content.")
    if content.is_deleted:
        raise PermissionDenied("Content was deleted.")
    if content.status != Content.Status.PENDING:
        raise PermissionDenied("Only pending content can be approved.")

    moderator_university_id = _resolve_university_id(moderator)
    if not moderator_university_id:
        raise PermissionDenied("Supervisor is not assigned to a university.")
    if content.university_id != moderator_university_id:
        raise PermissionDenied("You are not allowed to approve content from another university.")

    content.status = Content.Status.APPROVED
    content.approved_by = moderator
    content.approved_at = timezone.now()
    content.rejection_reason = ""
    content.save()

    CommunityApprovalLog.objects.create(
        post=content,
        author=content.author,
        approving_supervisor=moderator,
        decision=CommunityApprovalLog.Decision.APPROVED,
        university=content.university,
    )

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
    role_name = getattr(getattr(moderator, "role", None), "name", None)
    if role_name != Role.SUPERVISOR:
        raise PermissionDenied("You are not allowed to reject content.")
    if content.is_deleted:
        raise PermissionDenied("Content was deleted.")
    if content.status != Content.Status.PENDING:
        raise PermissionDenied("Only pending content can be rejected.")

    moderator_university_id = _resolve_university_id(moderator)
    if not moderator_university_id:
        raise PermissionDenied("Supervisor is not assigned to a university.")
    if content.university_id != moderator_university_id:
        raise PermissionDenied("You are not allowed to reject content from another university.")

    content.status = Content.Status.REJECTED
    content.rejection_reason = reason
    content.approved_by = moderator
    content.approved_at = timezone.now()
    content.save()

    CommunityApprovalLog.objects.create(
        post=content,
        author=content.author,
        approving_supervisor=moderator,
        decision=CommunityApprovalLog.Decision.REJECTED,
        reason=reason,
        university=content.university,
    )

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
    if content.is_deleted:
        raise PermissionDenied("Content was deleted.")
    if content.status != Content.Status.APPROVED:
        raise PermissionDenied("Only approved content can be liked.")

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
    role_name = getattr(getattr(user, "role", None), "name", None)
    if not role_name:
        raise PermissionDenied("User role is missing; contact admin.")
    if role_name not in {Role.STUDENT, Role.SUPERVISOR}:
        raise PermissionDenied("You are not allowed to comment on content.")
    if content.is_deleted:
        raise PermissionDenied("Content was deleted.")
    if content.status != Content.Status.APPROVED:
        raise PermissionDenied("You can only comment on approved content.")

    user_university_id = _resolve_university_id(user)
    if not user_university_id:
        raise PermissionDenied("User is not assigned to a university.")
    if content.university_id != user_university_id:
        raise PermissionDenied("You are not allowed to comment on content from another university.")

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


def update_content(*, user, content: Content, data: dict) -> Content:
    if content.is_deleted:
        raise PermissionDenied("Content was deleted.")
    if content.status != Content.Status.PENDING:
        raise PermissionDenied("Approved content cannot be modified.")
    if content.author_id != user.id:
        raise PermissionDenied("You can only update your own content.")

    for field, value in data.items():
        setattr(content, field, value)
    content.full_clean()
    content.save()
    return content


def delete_content(*, user, content: Content) -> Content:
    role_name = getattr(getattr(user, "role", None), "name", None)
    if content.is_deleted:
        return content

    if role_name == Role.STUDENT:
        if content.author_id != user.id:
            raise PermissionDenied("You can only delete your own content.")
        if content.status != Content.Status.PENDING:
            raise PermissionDenied("You can only delete pending content.")
    elif role_name == Role.UNIVERSITY_ADMIN:
        user_university_id = _resolve_university_id(user)
        if not user_university_id:
            raise PermissionDenied("University Admin is not assigned to a university.")
        if content.university_id != user_university_id:
            raise PermissionDenied("You are not allowed to delete content from another university.")
    else:
        raise PermissionDenied("You are not allowed to delete content.")

    content.is_deleted = True
    content.deleted_at = timezone.now()
    content.deleted_by = user
    content.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])

    log_audit_event(
        user=user,
        university=content.university,
        action="community.content.deleted",
        description="Community content deleted",
        content_object=content,
    )

    return content
