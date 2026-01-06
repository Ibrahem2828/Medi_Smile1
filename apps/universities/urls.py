# apps/universities/urls.py
from django.urls import path

from .views import (
    UniversityListView,
    UniversityCreateView,
    UniversityDetailView,
    UniversityUpdateView,
    UniversityDeleteView,
    FacultyListCreateView,
    FacultyRetrieveUpdateDeleteView,
    AcademicProgramListCreateView,
    AcademicProgramRetrieveUpdateDeleteView,
    AcademicYearListCreateView,
    AcademicYearRetrieveUpdateDeleteView,
    CourseListCreateView,
    CourseRetrieveUpdateDeleteView,
    UniversityAdminUpdateView,
    StudentUniversitySelectionView,
)

urlpatterns = [
    # =====================================================
    # Universities (System Level)
    # =====================================================
    path("", UniversityListView.as_view(), name="university-list"),
    path("create/", UniversityCreateView.as_view(), name="university-create"),
    path("<uuid:pk>/", UniversityDetailView.as_view(), name="university-detail"),
    path("<uuid:pk>/update/", UniversityUpdateView.as_view(), name="university-update"),
    path("<uuid:pk>/delete/", UniversityDeleteView.as_view(), name="university-delete"),
    path("me/update/", UniversityAdminUpdateView.as_view(), name="university-admin-update"),
    path("me/university-selection/", StudentUniversitySelectionView.as_view(), name="student-university-selection"),
    # Accept without trailing slash to avoid APPEND_SLASH POST errors
    path("me/university-selection", StudentUniversitySelectionView.as_view(), name="student-university-selection-noslash"),

    # =====================================================
    # Faculties (University Admin)
    # =====================================================
    path("faculties/", FacultyListCreateView.as_view(), name="faculty-list-create"),
    path("faculties/<uuid:pk>/", FacultyRetrieveUpdateDeleteView.as_view(), name="faculty-detail"),

    # =====================================================
    # Academic Programs (University Admin)
    # =====================================================
    path(
        "programs/",
        AcademicProgramListCreateView.as_view(),
        name="program-list-create",
    ),
    path(
        "programs/<uuid:pk>/",
        AcademicProgramRetrieveUpdateDeleteView.as_view(),
        name="program-detail",
    ),

    # =====================================================
    # Academic Years (University Admin)
    # =====================================================
    path(
        "academic-years/",
        AcademicYearListCreateView.as_view(),
        name="academic-year-list-create",
    ),
    path(
        "academic-years/<uuid:pk>/",
        AcademicYearRetrieveUpdateDeleteView.as_view(),
        name="academic-year-detail",
    ),

    # =====================================================
    # Courses (University Admin)
    # =====================================================
    path("courses/", CourseListCreateView.as_view(), name="course-list-create"),
    path("courses/<uuid:pk>/", CourseRetrieveUpdateDeleteView.as_view(), name="course-detail"),
]
