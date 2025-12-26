# apps/notifications/audit_bridge.py
from __future__ import annotations

from typing import Any

from apps.notifications.services import notify_user


def notify_on_audit_event(*, action: str, context: dict[str, Any]):
    """
    Bridge layer: maps audit actions to notifications.

    Keep it small + explicit.
    This ensures:
    - Services remain clean
    - Notification logic stays centralized
    """

    if action == "community.content.approved":
        notify_user(
            recipient=context["author"],
            notification_type="community_content_approved",
            title="تمت الموافقة على منشورك",
            message="تمت الموافقة على منشورك ونشره في مجتمع الجامعة.",
            target_object=context.get("content_object"),
            payload={"content_id": str(context["content_id"])},
        )

    elif action == "community.content.rejected":
        notify_user(
            recipient=context["author"],
            notification_type="community_content_rejected",
            title="تم رفض منشورك",
            message="تم رفض منشورك. يمكنك تعديل المحتوى وإعادة الإرسال.",
            target_object=context.get("content_object"),
            payload={
                "content_id": str(context["content_id"]),
                "reason": context.get("reason"),
            },
            priority="high" if context.get("reason") else "normal",
        )

    elif action == "reports.report.submitted":
        supervisor = context.get("supervisor")
        if supervisor:
            notify_user(
                recipient=supervisor,
                notification_type="report_submitted",
                title="تقرير جديد بانتظار المراجعة",
                message="قام الطالب بإرسال تقرير حالة جديد. الرجاء مراجعته.",
                target_object=context.get("report_object"),
                payload={
                    "report_id": str(context["report_id"]),
                    "case_id": str(context.get("case_id")) if context.get("case_id") else None,
                },
            )
