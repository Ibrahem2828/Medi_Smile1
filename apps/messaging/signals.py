# apps/messaging/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Message


@receiver(post_save, sender=Message)
def on_message_created(sender, instance: Message, created: bool, **kwargs):
    """
    Triggered when a new message is sent.

    Future responsibilities:
    - Push notification to receiver
    - Audit log (who sent, case, timestamp)
    - Update unread counters
    """
    if not created:
        return

    # Example (future):
    # notify_user(instance)
    # audit_log.record_message(instance)
    pass
