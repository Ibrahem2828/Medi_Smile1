import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class Attachment(models.Model):
    """Attachment model."""
    
    TYPE_CHOICES = (
        ('image', _('Image')),
        ('document', _('Document')),
        ('video', _('Video')),
        ('audio', _('Audio')),
        ('other', _('Other')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='attachments/', verbose_name=_('File'))
    original_filename = models.CharField(max_length=255, verbose_name=_('Original Filename'))
    file_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name=_('File Type'))
    file_size = models.PositiveIntegerField(verbose_name=_('File Size (bytes)'))
    mime_type = models.CharField(max_length=100, verbose_name=_('MIME Type'))
    
    # Reference to related objects
    case_id = models.UUIDField(blank=True, null=True, verbose_name=_('Case ID'))
    appointment_id = models.UUIDField(blank=True, null=True, verbose_name=_('Appointment ID'))
    message_id = models.UUIDField(blank=True, null=True, verbose_name=_('Message ID'))
    content_id = models.UUIDField(blank=True, null=True, verbose_name=_('Content ID'))
    
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='uploaded_attachments',
        verbose_name=_('Uploaded By')
    )
    is_public = models.BooleanField(default=False, verbose_name=_('Is Public'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        db_table = 'attachments'
        verbose_name = _('Attachment')
        verbose_name_plural = _('Attachments')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.original_filename
    
    def get_file_extension(self):
        """Get file extension."""
        return self.original_filename.split('.')[-1].lower()
    
    def is_image(self):
        """Check if file is an image."""
        return self.file_type == 'image'
    
    def is_document(self):
        """Check if file is a document."""
        return self.file_type == 'document'
    
    def is_video(self):
        """Check if file is a video."""
        return self.file_type == 'video'
    
    def is_audio(self):
        """Check if file is an audio."""
        return self.file_type == 'audio'