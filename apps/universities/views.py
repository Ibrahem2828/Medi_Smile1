# apps/universities/views.py
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.exceptions import PermissionDenied

from .models import University, Faculty, AcademicProgram, AcademicYear, Course, get_or_create_dentistry_faculty
from .serializers import (
    UniversityListSerializer,
    UniversityDetailSerializer,
    UniversityCreateSerializer,
    FacultySerializer,
    AcademicProgramSerializer,
    AcademicYearSerializer,
    CourseSerializer,
    StudentUniversitySelectionSerializer,
)

from apps.accounts.permissions import IsUniversityAdmin, IsTechSupport
from apps.accounts.models import Role, StudentProfile


# ============================================================
# Permissions
# ============================================================

class CanManageUniversity(BasePermission):
    """
    Tech Support: manage any university.
    University Admin: manage only his own university.
    """

    def has_permission(self, request, view):
        return bool(getattr(request.user, "is_authenticated", False))

    def has_object_permission(self, request, view, obj):
        role_name = getattr(getattr(request.user, "role", None), "name", None)
        if role_name == "tech_support":
            return True
        if role_name == "university_admin":
            try:
                admin_univ = request.user.universityadminprofile_profile.university_id
            except Exception:
                return False
            return admin_univ == obj.id
        return False


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
    except (AttributeError, ObjectDoesNotExist):
        # When a university_admin user lacks a linked profile, surface a clear 403 instead of crashing.
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


class FacultyRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve/Update/Delete faculty within the admin's university.
    """
    serializer_class = FacultySerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def get_queryset(self):
        university = get_admin_university(self.request)
        return Faculty.objects.filter(university=university)


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


class AcademicProgramRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve/Update/Delete academic program within the admin's university.
    """
    serializer_class = AcademicProgramSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def get_queryset(self):
        university = get_admin_university(self.request)
        return AcademicProgram.objects.filter(university=university)


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


class AcademicYearRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve/Update/Delete academic year within the admin's university.
    """
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def get_queryset(self):
        university = get_admin_university(self.request)
        return AcademicYear.objects.filter(university=university)


# ============================================================
# Courses (University Admin Scoped)
# ============================================================

class CourseListCreateView(generics.ListCreateAPIView):
    """
    List & create courses within the admin's university.
    """
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def get_queryset(self):
        university = get_admin_university(self.request)
        # Ensure default faculty exists for the university
        get_or_create_dentistry_faculty(university)
        return Course.objects.filter(university=university, is_active=True).select_related(
            "university", "faculty", "academic_year", "program", "supervisor"
        ).prefetch_related("students")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["university"] = get_admin_university(self.request)
        return ctx

    def perform_create(self, serializer):
        university = get_admin_university(self.request)
        serializer.save(university=university)


class CourseRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a course within the admin's university.
    """
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def get_queryset(self):
        university = get_admin_university(self.request)
        return Course.objects.filter(university=university).select_related(
            "university", "faculty", "academic_year", "program", "supervisor"
        ).prefetch_related("students")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["university"] = get_admin_university(self.request)
        return ctx


# ============================================================
# University Admin Self-Update
# ============================================================

class UniversityAdminUpdateView(generics.UpdateAPIView):
    """
    University Admin can update ONLY his own university (profile-linked).
    """

    serializer_class = UniversityDetailSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def get_object(self):
        return get_admin_university(self.request)


# ============================================================
# Student: Choose University
# ============================================================

class StudentUniversitySelectionView(generics.GenericAPIView):
    """
    Student selects the university they belong to (or updates it).
    GET: current selection (or null if not set).
    POST: set/update selection.
    """

    serializer_class = StudentUniversitySelectionSerializer
    permission_classes = [IsAuthenticated]

    def _ensure_student(self, user):
        if getattr(getattr(user, "role", None), "name", None) != Role.STUDENT:
            raise PermissionDenied(_("Only students can select a university."))

    def get_profile(self, user):
        self._ensure_student(user)
        return StudentProfile.objects.filter(user=user).select_related("university").first()

    def get(self, request):
        user = request.user
        profile = self.get_profile(user)
        if not profile:
            return Response(
                {"status": "success", "message": _("No university selected yet."), "data": None},
                status=status.HTTP_200_OK,
            )
        data = self.get_serializer(profile).data
        return Response({"status": "success", "message": _("University retrieved."), "data": data})

    def post(self, request):
        user = request.user
        self._ensure_student(user)
        profile = StudentProfile.objects.filter(user=user).first()

        serializer = self.get_serializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        university = serializer.validated_data["university"]

        if profile:
            profile.university = university
            profile.save(update_fields=["university", "updated_at"])
        else:
            profile = StudentProfile.objects.create(user=user, university=university)

        return Response(
            {"status": "success", "message": _("University selected successfully."), "data": self.get_serializer(profile).data},
            status=status.HTTP_200_OK,
        )
