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

    # University scoped lists
    UniversityStudentsListView,
    UniversitySupervisorsListView,
    UniversityAdminsListView,
    UniversityAdminsByUniversityView,
    UniversityAdminsAllView,
    UniversityAdminStudentsManageView,
    UniversityAdminStudentDetailView,
    UniversityAdminSupervisorsManageView,
    UniversityAdminSupervisorDetailView,

    # Self profile
    PatientMeView,
    StudentMeView,
    SupervisorMeView,
    UniversityAdminMeView,
    TechSupportMeView,
    FCMTokenView,
    TechSupportUniversityAdminDetailView,
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
    path(
        "university/students/",
        UniversityStudentsListView.as_view(),
        name="university-students",
    ),
    path(
        "university/supervisors/",
        UniversitySupervisorsListView.as_view(),
        name="university-supervisors",
    ),
    path(
        "university/admins/",
        UniversityAdminsListView.as_view(),
        name="university-admins",
    ),
    path(
        "university/admins/by-university/",
        UniversityAdminsByUniversityView.as_view(),
        name="university-admins-by-university",
    ),
    path(
        "university/admins/all/",
        UniversityAdminsAllView.as_view(),
        name="university-admins-all",
    ),
    path(
        "university/students/manage/",
        UniversityAdminStudentsManageView.as_view(),
        name="university-students-manage",
    ),
    path(
        "university/students/manage/<uuid:user_id>/",
        UniversityAdminStudentDetailView.as_view(),
        name="university-student-detail",
    ),
    path(
        "university/supervisors/manage/",
        UniversityAdminSupervisorsManageView.as_view(),
        name="university-supervisors-manage",
    ),
    path(
        "university/supervisors/manage/<uuid:user_id>/",
        UniversityAdminSupervisorDetailView.as_view(),
        name="university-supervisor-detail",
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
    path("me/token/", FCMTokenView.as_view(), name="me-fcm-token"),

    # =====================================================
    # Tech Support manages University Admins
    # =====================================================
    path(
        "tech-support/university-admins/<uuid:user_id>/",
        TechSupportUniversityAdminDetailView.as_view(),
        name="ts-university-admin-detail",
    ),
]


