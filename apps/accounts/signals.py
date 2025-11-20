from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import (
    PatientProfile, StudentProfile, 
    SupervisorProfile, UniversityAdminProfile, TechSupportProfile
)

User = get_user_model()


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    """Create user profile based on role."""
    if created:
        if instance.role == 'patient':
            PatientProfile.objects.create(user=instance)
        elif instance.role == 'student':
            StudentProfile.objects.create(user=instance)
        elif instance.role == 'supervisor':
            SupervisorProfile.objects.create(user=instance)
        elif instance.role == 'university_admin':
            UniversityAdminProfile.objects.create(user=instance)
        elif instance.role == 'tech_support':
            TechSupportProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    """Save user profile based on role."""
    if instance.role == 'patient':
        instance.patientprofile_profile.save()
    elif instance.role == 'student':
        instance.studentprofile_profile.save()
    elif instance.role == 'supervisor':
        instance.supervisorprofile_profile.save()
    elif instance.role == 'university_admin':
        instance.universityadminprofile_profile.save()
    elif instance.role == 'tech_support':
        instance.techsupportprofile_profile.save()