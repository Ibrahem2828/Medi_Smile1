from django.urls import path

from .views import (
    # =====================================================
    # Universities (System / IT Support)
    # =====================================================
    UniversityListView,
    UniversityCreateView,
    UniversityDetailView,
    UniversityUpdateView,
    UniversityDeleteView,

    # =====================================================
    # University-scoped (University Admin)
    # =====================================================
    FacultyListCreateView,
    AcademicProgramListCreateView,
    AcademicYearListCreateView,
)

urlpatterns = [

    # =====================================================
    # Universities
    # =====================================================
    # List active universities (read-only for authenticated users)
    path(
        "",
        UniversityListView.as_view(),
        name="university-list",
    ),

    # Create university (IT Support only)
    path(
        "create/",
        UniversityCreateView.as_view(),
        name="university-create",
    ),

    # University detail
    path(
        "<uuid:pk>/",
        UniversityDetailView.as_view(),
        name="university-detail",
    ),

    # Update university (IT Support only)
    path(
        "<uuid:pk>/update/",
        UniversityUpdateView.as_view(),
        name="university-update",
    ),

    # Soft delete (deactivate) university (IT Support only)
    path(
        "<uuid:pk>/delete/",
        UniversityDeleteView.as_view(),
        name="university-delete",
    ),

    # =====================================================
    # University Admin Scoped Resources
    # =====================================================
    # Faculty management (scoped by admin's university)
    path(
        "faculties/",
        FacultyListCreateView.as_view(),
        name="faculty-list-create",
    ),

    # Academic programs management (scoped by admin's university)
    path(
        "programs/",
        AcademicProgramListCreateView.as_view(),
        name="academic-program-list-create",
    ),

    # Academic years management (scoped by admin's university)
    path(
        "academic-years/",
        AcademicYearListCreateView.as_view(),
        name="academic-year-list-create",
    ),
]
