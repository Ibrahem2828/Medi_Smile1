import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.cases.models import Case

User = settings.AUTH_USER_MODEL


# ============================================================
# Room (Case-based Conversation)
# ============================================================
class Room(models.Model):
    """
    Messaging room bound strictly to ONE medical Case.

    Participants are fixed and derived from the case:
    - Patient
    - Assigned Student
    (Supervisor may observe via permissions, not direct chat)
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    case = models.OneToOneField(
        Case,
        on_delete=models.CASCADE,
        related_name="chat_room",
        verbose_name=_("Case"),
        help_text=_("Each case has exactly one messaging room"),
    )

    participant_patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="patient_chat_rooms",
        verbose_name=_("Patient"),
    )

    participant_student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="student_chat_rooms",
        verbose_name=_("Student"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )

    class Meta:
        db_table = "messaging_rooms"
        verbose_name = _("Chat Room")
        verbose_name_plural = _("Chat Rooms")
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(
                    participant_patient=models.F("participant_student")
                ),
                name="room_participants_must_be_different",
            ),
        ]
        indexes = [
            models.Index(fields=["case"]),
            models.Index(fields=["participant_patient"]),
            models.Index(fields=["participant_student"]),
        ]

    def __str__(self) -> str:
        return f"Chat Room for Case {self.case_id}"


# ============================================================
# Message
# ============================================================
class Message(models.Model):
    """
    Single chat message inside a Room.
    Immutable once created (medical audit requirement).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Room"),
    )

    sender = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="sent_messages",
        verbose_name=_("Sender"),
    )

    content = models.TextField(
        verbose_name=_("Message Content"),
    )

    sent_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Sent At"),
    )

    is_system = models.BooleanField(
        default=False,
        verbose_name=_("System Message"),
        help_text=_("True if generated automatically by the system"),
    )

    class Meta:
        db_table = "messaging_messages"
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")
        ordering = ["sent_at"]
        indexes = [
            models.Index(fields=["room", "sent_at"]),
            models.Index(fields=["sender"]),
        ]

    def save(self, *args, **kwargs):
        """
        Prevent message modification after creation.
        """
        if self.pk:
            raise RuntimeError("Messages are immutable once created.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Message from {self.sender} at {self.sent_at}"
