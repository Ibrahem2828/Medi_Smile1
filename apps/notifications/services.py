"""
Notification delivery services.

Supports:
- Firebase Cloud Messaging (FCM)
- Graceful fallback when disabled
- Generic notification payloads
"""

from __future__ import annotations

import os
from typing import Optional, Dict, Any

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .models import Notification


# ============================================================
# Firebase Availability
# ============================================================

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


# ============================================================
# Firebase Initialization
# ============================================================

def initialize_firebase() -> bool:
    """
    Initialize Firebase Admin SDK (singleton-safe).

    Returns:
        bool: True if initialized or already initialized.
    """
    if not FIREBASE_AVAILABLE:
        return False

    try:
        firebase_admin.get_app()
        return True
    except ValueError:
        pass  # Not initialized yet

    try:
        # Priority 1: ENV path
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            return True

        # Priority 2: Django settings dict
        cred_dict = getattr(settings, "FIREBASE_CREDENTIALS", None)
        if cred_dict:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            return True

    except Exception as exc:
        # Silent fail (do not break business logic)
        print(f"[FCM] Initialization failed: {exc}")

    return False


# ============================================================
# Low-level Push Sender
# ============================================================

def send_push_notification(
    *,
    fcm_token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Send a push notification via Firebase Cloud Messaging.

    This function NEVER raises.
    """

    if not FIREBASE_AVAILABLE:
        return False

    if not initialize_firebase():
        return False

    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={k: str(v) for k, v in (data or {}).items()},
            token=fcm_token,
        )

        messaging.send(message)
        return True

    except Exception as exc:
        print(f"[FCM] Send failed: {exc}")
        return False


# ============================================================
# Payload Builder
# ============================================================

def build_notification_payload(notification: Notification) -> Dict[str, Any]:
    """
    Build a unified payload for mobile / frontend clients.
    """

    payload = {
        "notification_id": str(notification.id),
        "type": notification.notification_type,
        "status": notification.status,
        "priority": notification.priority,
    }

    if notification.appointment_id:
        payload["appointment_id"] = str(notification.appointment_id)

    if notification.target_content_type:
        payload["target_type"] = notification.target_content_type.model
        payload["target_id"] = str(notification.target_object_id)

    return payload


# ============================================================
# High-level Dispatcher
# ============================================================

def dispatch_notification(notification: Notification) -> bool:
    """
    Dispatch notification to recipient using all available channels.

    Currently:
    - Push (FCM)

    Future:
    - WebSocket
    - Email
    """

    recipient = notification.recipient

    # Push notifications
    if hasattr(recipient, "fcm_token") and recipient.fcm_token:
        return send_push_notification(
            fcm_token=recipient.fcm_token,
            title=notification.title,
            body=notification.message,
            data=build_notification_payload(notification),
        )

    return False


# ============================================================
# Backward Compatible Helper
# ============================================================

def send_notification_to_user(user, notification: Notification) -> bool:
    """
    Backward-compatible wrapper.

    DO NOT REMOVE.
    """
    return dispatch_notification(notification)
