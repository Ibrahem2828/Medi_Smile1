import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.accounts.models import User


class Content(models.Model):
    """Content model for community resources."""
    
    TYPE_CHOICES = (
        ('article', _('Article')),
        ('video', _('Video')),
        ('document', _('Document')),
        ('image', _('Image')),
        ('link', _('Link')),
    )
    
    CATEGORY_CHOICES = (
        ('medical', _('Medical')),
        ('educational', _('Educational')),
        ('research', _('Research')),
        ('news', _('News')),
        ('general', _('General')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, verbose_name=_('Title'))
    description = models.TextField(verbose_name=_('Description'))
    content_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name=_('Content Type'))
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name=_('Category'))
    file = models.FileField(upload_to='community_files/', blank=True, null=True, verbose_name=_('File'))
    url = models.URLField(blank=True, null=True, verbose_name=_('URL'))
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='authored_content',
        verbose_name=_('Author')
    )
    university = models.ForeignKey(
        'universities.University', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='content',
        verbose_name=_('University')
    )
    tags = models.CharField(max_length=500, blank=True, null=True, verbose_name=_('Tags'))
    is_public = models.BooleanField(default=True, verbose_name=_('Is Public'))
    is_featured = models.BooleanField(default=False, verbose_name=_('Is Featured'))
    
    # Approval system for student posts
    STATUS_CHOICES = (
        ('pending', _('Pending Approval')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='approved',
        verbose_name=_('Status'),
        help_text=_('For students: requires supervisor approval. Others: auto-approved.')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_content',
        limit_choices_to={'role__in': ['supervisor', 'university_admin', 'tech_support']},
        verbose_name=_('Approved By'),
        help_text=_('Supervisor or admin who approved/rejected this content')
    )
    rejection_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Rejection Reason'),
        help_text=_('Reason for rejection if status is rejected')
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Approved At')
    )
    
    view_count = models.PositiveIntegerField(default=0, verbose_name=_('View Count'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        db_table = 'community_content'
        verbose_name = _('Content')
        verbose_name_plural = _('Content')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'author']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return self.title


class ContentLike(models.Model):
    """Content like model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.ForeignKey(
        Content, 
        on_delete=models.CASCADE, 
        related_name='likes',
        verbose_name=_('Content')
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='liked_content',
        verbose_name=_('User')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        db_table = 'content_likes'
        verbose_name = _('Content Like')
        verbose_name_plural = _('Content Likes')
        unique_together = ['content', 'user']
    
    def __str__(self):
        return f"{self.user.username} likes {self.content.title}"


class ContentComment(models.Model):
    """Content comment model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.ForeignKey(
        Content, 
        on_delete=models.CASCADE, 
        related_name='comments',
        verbose_name=_('Content')
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='comments',
        verbose_name=_('User')
    )
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        related_name='replies',
        verbose_name=_('Parent Comment')
    )
    text = models.TextField(verbose_name=_('Text'))
    is_approved = models.BooleanField(default=True, verbose_name=_('Is Approved'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        db_table = 'content_comments'
        verbose_name = _('Content Comment')
        verbose_name_plural = _('Content Comments')
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.text[:50]}..."