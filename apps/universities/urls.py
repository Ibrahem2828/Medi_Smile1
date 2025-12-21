# apps/universities/urls.py

from django.urls import path

from .views import (
    UniversityListView,
    UniversityCreateView,
    UniversityDetailView,
    UniversityUpdateView,
    UniversityDeleteView,
    FacultyListCreateView,
    AcademicProgramListCreateView,
    AcademicYearListCreateView,
)

urlpatterns = [
    # =====================================================
    # Universities
    # =====================================================
    path(
        "",
        UniversityListView.as_view(),
        name="university-list",
    ),
    path(
        "create/",
        UniversityCreateView.as_view(),
        name="university-create",
    ),
    path(
        "<uuid:pk>/",
        UniversityDetailView.as_view(),
        name="university-detail",
    ),
    path(
        "<uuid:pk>/update/",
        UniversityUpdateView.as_view(),
        name="university-update",
    ),
    path(
        "<uuid:pk>/delete/",
        UniversityDeleteView.as_view(),
        name="university-delete",
    ),

    # =====================================================
    # Faculties
    # =====================================================
    path(
        "<uuid:university_id>/faculties/",
        FacultyListCreateView.as_view(),
        name="faculty-list-create",
    ),

    # =====================================================
    # Academic Programs
    # =====================================================
    path(
        "<uuid:university_id>/programs/",
        AcademicProgramListCreateView.as_view(),
        name="academic-program-list-create",
    ),

    # =====================================================
    # Academic Years
    # =====================================================
    path(
        "<uuid:university_id>/academic-years/",
        AcademicYearListCreateView.as_view(),
        name="academic-year-list-create",
    ),
]
