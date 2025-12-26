# apps/universities/views.py
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import University, Faculty, AcademicProgram, AcademicYear
from .serializers import (
    UniversityListSerializer,
    UniversityDetailSerializer,
    UniversityCreateSerializer,
    FacultySerializer,
    AcademicProgramSerializer,
    AcademicYearSerializer,
)

from apps.accounts.permissions import IsUniversityAdmin, IsTechSupport


# ============================================================
# Helpers (University Scoping)
# ============================================================

def get_admin_university(request):
    """
    Returns the university linked to the logged-in University Admin.
    Prevents cross-university access.
    """
    try:
        profile = request.user.universityadminprofile_profile
    except ObjectDoesNotExist:
        raise PermissionDenied(_("University Admin profile not found."))

    if not profile.university:
        raise PermissionDenied(_("University Admin is not assigned to a university."))

    return profile.university


# ============================================================
# University Views (System Level)
# ============================================================

class UniversityListView(generics.ListAPIView):
    """
    List active universities.
    Visible to authenticated users (read-only).
    """
    queryset = University.objects.filter(is_active=True)
    serializer_class = UniversityListSerializer
    permission_classes = [IsAuthenticated]


class UniversityCreateView(generics.CreateAPIView):
    """
    Create university.
    🔐 Only IT Support.
    """
    serializer_class = UniversityCreateSerializer
    permission_classes = [IsAuthenticated, IsTechSupport]


class UniversityDetailView(generics.RetrieveAPIView):
    queryset = University.objects.all()
    serializer_class = UniversityDetailSerializer
    permission_classes = [IsAuthenticated]


class UniversityUpdateView(generics.UpdateAPIView):
    """
    Update university data.
    🔐 Only IT Support.
    """
    queryset = University.objects.all()
    serializer_class = UniversityDetailSerializer
    permission_classes = [IsAuthenticated, IsTechSupport]


class UniversityDeleteView(generics.DestroyAPIView):
    """
    Soft delete (deactivate) university.
    🔐 Only IT Support.
    """
    queryset = University.objects.all()
    permission_classes = [IsAuthenticated, IsTechSupport]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


# ============================================================
# Faculty Views (University Admin Scoped)
# ============================================================

class FacultyListCreateView(generics.ListCreateAPIView):
    """
    List & create faculties within the admin's university.
    """
    serializer_class = FacultySerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def get_queryset(self):
        university = get_admin_university(self.request)
        return Faculty.objects.filter(
            university=university,
            is_active=True,
        )

    def perform_create(self, serializer):
        university = get_admin_university(self.request)
        serializer.save(university=university)


# ============================================================
# Academic Program Views (University Admin Scoped)
# ============================================================

class AcademicProgramListCreateView(generics.ListCreateAPIView):
    """
    List & create academic programs within the admin's university.
    """
    serializer_class = AcademicProgramSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def get_queryset(self):
        university = get_admin_university(self.request)
        return AcademicProgram.objects.filter(
            university=university,
            is_active=True,
        )

    def perform_create(self, serializer):
        university = get_admin_university(self.request)
        serializer.save(university=university)


# ============================================================
# Academic Year Views (University Admin Scoped)
# ============================================================

class AcademicYearListCreateView(generics.ListCreateAPIView):
    """
    List & create academic years within the admin's university.
    """
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def get_queryset(self):
        university = get_admin_university(self.request)
        return AcademicYear.objects.filter(university=university)

    def perform_create(self, serializer):
        university = get_admin_university(self.request)
        serializer.save(university=university)
