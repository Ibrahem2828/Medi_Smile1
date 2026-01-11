import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.accounts.models import Role
from apps.cases.models import Case
from apps.universities.models import Course

User = settings.AUTH_USER_MODEL


# ============================================================
# Room (Case-based Conversation)
# ============================================================
class Room(models.Model):
    """
    Messaging room bound to either a Case or a Course.

    Thread types:
    - case: patient <-> assigned student
    - course: student <-> course supervisor
    """

    class ThreadType(models.TextChoices):
        CASE = "case", _("Case")
        COURSE = "course", _("Course")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    thread_type = models.CharField(
        max_length=20,
        choices=ThreadType.choices,
        default=ThreadType.CASE,
        verbose_name=_("Thread Type"),
    )

    case = models.OneToOneField(
        Case,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_room",
        verbose_name=_("Case"),
        help_text=_("Each case has exactly one messaging room"),
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_rooms",
        verbose_name=_("Course"),
    )

    participant_patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="patient_chat_rooms",
        verbose_name=_("Patient"),
    )

    participant_student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="student_chat_rooms",
        verbose_name=_("Student"),
    )

    participant_supervisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="supervisor_chat_rooms",
        verbose_name=_("Supervisor"),
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
            models.CheckConstraint(
                check=~models.Q(
                    participant_supervisor=models.F("participant_student")
                ),
                name="room_supervisor_student_must_be_different",
            ),
            models.UniqueConstraint(
                fields=["course", "participant_student", "participant_supervisor", "thread_type"],
                name="room_unique_course_thread",
            ),
        ]
        indexes = [
            models.Index(fields=["case"]),
            models.Index(fields=["course"]),
            models.Index(fields=["participant_patient"]),
            models.Index(fields=["participant_student"]),
            models.Index(fields=["participant_supervisor"]),
        ]

    def clean(self):
        super().clean()

        if self.thread_type == self.ThreadType.CASE:
            if not self.case_id:
                raise ValidationError({"case": _("Case is required for case threads.")})
            if self.course_id:
                raise ValidationError({"course": _("Course must be empty for case threads.")})
            if not self.participant_patient_id or not self.participant_student_id:
                raise ValidationError(_("Case threads require patient and student participants."))
            if self.participant_supervisor_id:
                raise ValidationError({"participant_supervisor": _("Supervisor is not a chat participant for case threads.")})
            if self.case_id:
                if self.case.patient_id and self.participant_patient_id != self.case.patient_id:
                    raise ValidationError({"participant_patient": _("Participant patient must match the case patient.")})
                if self.case.student_id and self.participant_student_id != self.case.student_id:
                    raise ValidationError({"participant_student": _("Participant student must match the case student.")})

        elif self.thread_type == self.ThreadType.COURSE:
            if not self.course_id:
                raise ValidationError({"course": _("Course is required for course threads.")})
            if self.case_id:
                raise ValidationError({"case": _("Case must be empty for course threads.")})
            if not self.participant_student_id or not self.participant_supervisor_id:
                raise ValidationError(_("Course threads require student and supervisor participants."))
            if self.participant_patient_id:
                raise ValidationError({"participant_patient": _("Patient is not allowed in course threads.")})
            if self.course_id:
                if self.course.supervisor_id and self.participant_supervisor_id != self.course.supervisor_id:
                    raise ValidationError({"participant_supervisor": _("Participant supervisor must match the course supervisor.")})
                if self.participant_student_id and not self.course.students.filter(id=self.participant_student_id).exists():
                    raise ValidationError({"participant_student": _("Student must be enrolled in the course.")})

        else:
            raise ValidationError({"thread_type": _("Invalid thread type.")})

        if self.participant_student_id and getattr(self.participant_student, "role", None):
            if self.participant_student.role.name != Role.STUDENT:
                raise ValidationError({"participant_student": _("Participant student must have student role.")})
        if self.participant_supervisor_id and getattr(self.participant_supervisor, "role", None):
            if self.participant_supervisor.role.name != Role.SUPERVISOR:
                raise ValidationError({"participant_supervisor": _("Participant supervisor must have supervisor role.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.thread_type == self.ThreadType.COURSE:
            return f"Chat Room for Course {self.course_id}"
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
        if not self._state.adding:
            raise RuntimeError("Messages are immutable once created.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Message from {self.sender} at {self.sent_at}"
