"""
Firebase Cloud Messaging service for push notifications.
"""
import os
import json
from typing import Optional, Dict, Any
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .models import Notification


try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


def initialize_firebase():
    """Initialize Firebase Admin SDK."""
    if not FIREBASE_AVAILABLE:
        return False
    
    try:
        # Check if Firebase is already initialized
        firebase_admin.get_app()
        return True
    except ValueError:
        # Initialize Firebase
        try:
            # Try to get credentials from environment variable or file
            cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                return True
            else:
                # Try to get from settings
                cred_dict = getattr(settings, 'FIREBASE_CREDENTIALS', None)
                if cred_dict:
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                    return True
        except Exception as e:
            print(f"Firebase initialization error: {e}")
            return False
    
    return False


def send_push_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Send push notification via Firebase Cloud Messaging.
    
    Args:
        fcm_token: FCM token of the recipient device
        title: Notification title
        body: Notification body
        data: Additional data payload (optional)
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    if not FIREBASE_AVAILABLE:
        return False
    
    if not initialize_firebase():
        return False
    
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            token=fcm_token
        )
        
        response = messaging.send(message)
        print(f"Successfully sent message: {response}")
        return True
    except Exception as e:
        print(f"Error sending push notification: {e}")
        return False


def send_notification_to_user(
    user,
    notification: Notification
) -> bool:
    """
    Send push notification to user when a notification is created.
    
    Args:
        user: User object (must have fcm_token attribute)
        notification: Notification object
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    # Check if user has FCM token
    if not hasattr(user, 'fcm_token') or not user.fcm_token:
        return False
    
    # Prepare notification data
    data = {
        'notification_id': str(notification.id),
        'notification_type': notification.notification_type,
        'appointment_id': str(notification.appointment.id) if notification.appointment else '',
        'content_id': str(notification.content.id) if notification.content else '',
        'status': notification.status,
    }
    
    return send_push_notification(
        fcm_token=user.fcm_token,
        title=notification.title,
        body=notification.message,
        data=data
    )



















