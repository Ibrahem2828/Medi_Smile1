from django.contrib import admin
from .models import User, PatientProfile, StudentProfile, SupervisorProfile, UniversityAdminProfile, TechSupportProfile

admin.site.register(User)
admin.site.register(PatientProfile)
admin.site.register(StudentProfile)
admin.site.register(SupervisorProfile)
admin.site.register(UniversityAdminProfile)
admin.site.register(TechSupportProfile)
