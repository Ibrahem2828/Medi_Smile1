# apps/accounts/urls.py
from django.urls import path

from .views import (
    # Auth
    LoginView,
    LogoutView,

    # Patient
    PatientCreateView,
    PatientListView,
    PatientDetailView,
    PatientUpdateView,

    # Student
    StudentCreateView,
    StudentListView,
    StudentDetailView,
    StudentUpdateView,

    # Supervisor
    SupervisorCreateView,
    SupervisorListView,
    SupervisorDetailView,
    SupervisorUpdateView,

    # University Admin
    UniversityAdminCreateView,
    UniversityAdminListView,
    UniversityAdminDetailView,
    UniversityAdminUpdateView,

    # Tech Support (System)
    TechSupportCreateView,
    TechSupportListView,
    TechSupportDetailView,
    TechSupportUpdateView,
)

urlpatterns = [

    # ============================================================
    # AUTH
    # ============================================================
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),

    # ============================================================
    # PATIENT
    # ============================================================
    path("patients/register/", PatientCreateView.as_view(), name="patient-register"),
    path("patients/", PatientListView.as_view(), name="patient-list"),
    path("patients/<uuid:user_id>/", PatientDetailView.as_view(), name="patient-detail"),
    path("patients/<uuid:user_id>/update/", PatientUpdateView.as_view(), name="patient-update"),

    # ============================================================
    # STUDENT
    # ============================================================
    path("students/", StudentListView.as_view(), name="student-list"),
    path("students/create/", StudentCreateView.as_view(), name="student-create"),
    path("students/<uuid:user_id>/", StudentDetailView.as_view(), name="student-detail"),
    path("students/<uuid:user_id>/update/", StudentUpdateView.as_view(), name="student-update"),

    # ============================================================
    # SUPERVISOR
    # ============================================================
    path("supervisors/", SupervisorListView.as_view(), name="supervisor-list"),
    path("supervisors/create/", SupervisorCreateView.as_view(), name="supervisor-create"),
    path("supervisors/<uuid:user_id>/", SupervisorDetailView.as_view(), name="supervisor-detail"),
    path("supervisors/<uuid:user_id>/update/", SupervisorUpdateView.as_view(), name="supervisor-update"),

    # ============================================================
    # UNIVERSITY ADMIN
    # ============================================================
    path("university-admins/", UniversityAdminListView.as_view(), name="university-admin-list"),
    path("university-admins/create/", UniversityAdminCreateView.as_view(), name="university-admin-create"),
    path("university-admins/<uuid:user_id>/", UniversityAdminDetailView.as_view(), name="university-admin-detail"),
    path("university-admins/<uuid:user_id>/update/", UniversityAdminUpdateView.as_view(), name="university-admin-update"),

    # ============================================================
    # TECH SUPPORT (SYSTEM / INTERNAL)
    # ============================================================
    path("system/tech-support/create/", TechSupportCreateView.as_view(), name="tech-support-create"),
    path("system/tech-support/", TechSupportListView.as_view(), name="tech-support-list"),
    path("system/tech-support/<uuid:user_id>/", TechSupportDetailView.as_view(), name="tech-support-detail"),
    path("system/tech-support/<uuid:user_id>/update/", TechSupportUpdateView.as_view(), name="tech-support-update"),
]
