import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class University(models.Model):
    """University model."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Address'))
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('City'))
    country = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Country'))
    website = models.URLField(blank=True, null=True, verbose_name=_('Website'))
    email = models.EmailField(blank=True, null=True, verbose_name=_('Email'))
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Phone'))
    logo = models.ImageField(upload_to='university_logos/', blank=True, null=True, verbose_name=_('Logo'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        db_table = 'universities'
        verbose_name = _('University')
        verbose_name_plural = _('Universities')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Course(models.Model):
    """Course model."""
    
    LEVEL_CHOICES = (
        ('bachelor', _('Bachelor')),
        ('master', _('Master')),
        ('doctorate', _('Doctorate')),
        ('diploma', _('Diploma')),
        ('certificate', _('Certificate')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='courses', verbose_name=_('University'))
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    code = models.CharField(max_length=50, verbose_name=_('Code'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Description'))
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='bachelor', verbose_name=_('Level'))
    duration_years = models.PositiveIntegerField(default=4, verbose_name=_('Duration (Years)'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        db_table = 'courses'
        verbose_name = _('Course')
        verbose_name_plural = _('Courses')
        ordering = ['name']
        unique_together = ['university', 'code']
    
    def __str__(self):
        return f"{self.name} ({self.code})"