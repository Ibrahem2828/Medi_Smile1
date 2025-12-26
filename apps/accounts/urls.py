# apps/accounts/urls.py
from django.urls import path

from .views import (
    # Login
    PatientLoginView,
    StudentLoginView,
    SupervisorLoginView,
    UniversityAdminLoginView,
    TechSupportLoginView,

    # Registration / Creation
    PatientRegisterView,
    StudentCreateView,
    SupervisorCreateView,
    UniversityAdminCreateView,
    TechSupportCreateView,

    # Self profile
    PatientMeView,
    StudentMeView,
    SupervisorMeView,
    UniversityAdminMeView,
    TechSupportMeView,
)

urlpatterns = [
    # =====================================================
    # AUTHENTICATION (Separated Login)
    # =====================================================
    path("login/patient/", PatientLoginView.as_view(), name="login-patient"),
    path("login/student/", StudentLoginView.as_view(), name="login-student"),
    path("login/supervisor/", SupervisorLoginView.as_view(), name="login-supervisor"),
    path(
        "login/university-admin/",
        UniversityAdminLoginView.as_view(),
        name="login-university-admin",
    ),
    path(
        "login/tech-support/",
        TechSupportLoginView.as_view(),
        name="login-tech-support",
    ),

    # =====================================================
    # REGISTRATION / CREATION
    # =====================================================
    path("register/patient/", PatientRegisterView.as_view(), name="register-patient"),

    path("create/student/", StudentCreateView.as_view(), name="create-student"),
    path("create/supervisor/", SupervisorCreateView.as_view(), name="create-supervisor"),
    path(
        "create/university-admin/",
        UniversityAdminCreateView.as_view(),
        name="create-university-admin",
    ),
    path(
        "create/tech-support/",
        TechSupportCreateView.as_view(),
        name="create-tech-support",
    ),

    # =====================================================
    # SELF PROFILE (ME)
    # =====================================================
    path("me/patient/", PatientMeView.as_view(), name="me-patient"),
    path("me/student/", StudentMeView.as_view(), name="me-student"),
    path("me/supervisor/", SupervisorMeView.as_view(), name="me-supervisor"),
    path(
        "me/university-admin/",
        UniversityAdminMeView.as_view(),
        name="me-university-admin",
    ),
    path("me/tech-support/", TechSupportMeView.as_view(), name="me-tech-support"),
]
