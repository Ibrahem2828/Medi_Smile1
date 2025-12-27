# apps/audit/services.py
from __future__ import annotations

import logging
from typing import Any, Optional
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from .models import AuditLog

logger = logging.getLogger(__name__)


@transaction.atomic
def log_audit_event(
    *,
    user,
    action: str,
    description: str | None = None,
    university=None,
    content_object=None,
    object_type: str | None = None,
    object_id=None,
    metadata: Optional[dict[str, Any]] = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog | None:
    """
    Central audit logger.

    - Fail-safe: never يكسر الـ API؛ أي استثناء يتم تسجيله وإرجاع None.
    - يفضّل تمرير content_object، وإلا يمكن تمرير object_type + object_id.
    """

    try:
        ct = None
        oid = None

        if content_object is not None:
            ct = ContentType.objects.get_for_model(content_object.__class__)
            oid = getattr(content_object, "id", None)
        elif object_type and object_id:
            try:
                ct = ContentType.objects.get(model=object_type.split(".")[-1])
                oid = object_id
            except ContentType.DoesNotExist:
                ct = None
                oid = None

        if description is None:
            description = action

        return AuditLog.objects.create(
            user=user,
            university=university,
            action=action,
            description=description,
            content_type=ct,
            object_id=oid,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    except Exception:
        logger.exception("Failed to write audit log: %s", action)
        return None
