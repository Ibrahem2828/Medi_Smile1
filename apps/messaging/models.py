from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Room(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rooms_as_participant1')
    participant2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rooms_as_participant2')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('participant1', 'participant2')]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(participant1=models.F('participant2')),
                name='room_participants_must_differ',
            ),
        ]
        indexes = [
            models.Index(fields=['participant1']),
            models.Index(fields=['participant2']),
        ]

    def __str__(self):
        return f"Room {self.id} ({self.participant1.email} <-> {self.participant2.email})"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='simple_sent_messages')
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message {self.id} in Room {self.room_id} by {self.sender.email}"

    class Meta:
        indexes = [
            models.Index(fields=['room', 'sent_at']),
            models.Index(fields=['room', 'is_read']),
        ]