from django.contrib.auth.models import update_last_login
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Role,
    User,
    PatientProfile,
    StudentProfile,
    SupervisorProfile,
    UniversityAdminProfile,
    TechSupportProfile,
)

from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    UserSerializer,
    PatientCreateSerializer,
    PatientListSerializer,
    PatientDetailSerializer,
    PatientUpdateSerializer,
    StudentCreateSerializer,
    StudentListSerializer,
    StudentDetailSerializer,
    StudentUpdateSerializer,
    SupervisorCreateSerializer,
    SupervisorListSerializer,
    SupervisorDetailSerializer,
    SupervisorUpdateSerializer,
    UniversityAdminCreateSerializer,
    UniversityAdminListSerializer,
    UniversityAdminDetailSerializer,
    UniversityAdminUpdateSerializer,
    TechSupportCreateSerializer,
    TechSupportListSerializer,
    TechSupportDetailSerializer,
    TechSupportUpdateSerializer,
)

from .permissions import (
    IsPatient,
    IsStudent,
    IsSupervisor,
    IsUniversityAdmin,
    IsTechSupport,
    IsSystemAdmin,
    IsOwnerOrReadOnly,
)

# ============================================================
# Unified API Response
# ============================================================
class APIResponse:
    @staticmethod
    def success(message, data=None, status_code=status.HTTP_200_OK):
        return Response(
            {"status": "success", "message": message, "data": data},
            status=status_code,
        )

    @staticmethod
    def error(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            {"status": "error", "message": message, "errors": errors},
            status=status_code,
        )


# ============================================================
# Helpers (Scoped Access)
# ============================================================
def _get_university_admin_university(request):
    """
    Returns the University instance for University Admin user.
    Raises PermissionDenied if not properly linked.
    """
    try:
        profile = request.user.universityadminprofile_profile
    except ObjectDoesNotExist:
        raise PermissionDenied("حساب إدارة الجامعة غير مكتمل (لا يوجد ملف UniversityAdminProfile).")

    if not profile.university:
        raise PermissionDenied("حساب إدارة الجامعة غير مرتبط بجامعة. يرجى ربط الحساب بجامعة أولاً.")

    return profile.university


# ============================================================
# AUTH
# ============================================================
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        update_last_login(None, user)

        return APIResponse.success(
            "تم تسجيل الدخول بنجاح.",
            {
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                "user": UserSerializer(user).data,
            },
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            return APIResponse.error("Token غير صالح.", status_code=400)

        return APIResponse.success("تم تسجيل الخروج.", status_code=205)


# ============================================================
# PATIENT
# ============================================================
class PatientCreateView(generics.CreateAPIView):
    """
    Patient self-registration.
    """
    serializer_class = PatientCreateSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()

        # Ensure profile exists (and validated by model clean/save)
        PatientProfile.objects.create(user=user)


class PatientListView(generics.ListAPIView):
    """
    Tech Support can view all patients.
    University Admin can view patients (read-only) scoped by their university,
    BUT patients are not university-scoped in your current schema.
    Therefore:
    - If you do not have a direct relation patient->university, we allow:
      Tech Support only (default safe).
    - If you later add scoping (via cases), implement it there, not here.
    """
    queryset = PatientProfile.objects.select_related("user")
    serializer_class = PatientListSerializer
    permission_classes = [IsAuthenticated, IsTechSupport]


class PatientDetailView(generics.RetrieveAPIView):
    queryset = PatientProfile.objects.select_related("user")
    serializer_class = PatientDetailSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = "user__id"


class PatientUpdateView(generics.UpdateAPIView):
    serializer_class = PatientUpdateSerializer
    permission_classes = [IsAuthenticated, IsPatient, IsOwnerOrReadOnly]

    def get_object(self):
        return get_object_or_404(PatientProfile, user=self.request.user)


# ============================================================
# STUDENT
# ============================================================
class StudentCreateView(generics.CreateAPIView):
    serializer_class = StudentCreateSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def perform_create(self, serializer):
        """
        University Admin creates student INSIDE their university scope.
        We enforce university at profile level (not from request payload).
        """
        university = _get_university_admin_university(self.request)

        user = serializer.save()

        # Create profile and enforce university scope
        StudentProfile.objects.create(user=user, university=university)


class StudentListView(generics.ListAPIView):
    serializer_class = StudentListSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def get_queryset(self):
        university = _get_university_admin_university(self.request)
        return StudentProfile.objects.select_related("user", "university").filter(university=university)


class StudentDetailView(generics.RetrieveAPIView):
    serializer_class = StudentDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        - Student can view self.
        - University Admin can view only within scope.
        - Tech Support can view all if needed later (not enabled here).
        """
        user = self.request.user

        base_qs = StudentProfile.objects.select_related("user", "university")

        if user.role.name == Role.STUDENT:
            return base_qs.filter(user=user)

        if user.role.name == Role.UNIVERSITY_ADMIN:
            university = _get_university_admin_university(self.request)
            return base_qs.filter(university=university)

        # Default: deny by empty queryset (safe)
        return base_qs.none()


class StudentUpdateView(generics.UpdateAPIView):
    serializer_class = StudentUpdateSerializer
    permission_classes = [IsAuthenticated, IsStudent, IsOwnerOrReadOnly]

    def get_object(self):
        return get_object_or_404(StudentProfile, user=self.request.user)


# ============================================================
# SUPERVISOR
# ============================================================
class SupervisorCreateView(generics.CreateAPIView):
    serializer_class = SupervisorCreateSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def perform_create(self, serializer):
        university = _get_university_admin_university(self.request)

        user = serializer.save()
        SupervisorProfile.objects.create(user=user, university=university)


class SupervisorListView(generics.ListAPIView):
    serializer_class = SupervisorListSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]

    def get_queryset(self):
        university = _get_university_admin_university(self.request)
        return SupervisorProfile.objects.select_related("user", "university").filter(university=university)


class SupervisorDetailView(generics.RetrieveAPIView):
    serializer_class = SupervisorDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base_qs = SupervisorProfile.objects.select_related("user", "university")

        if user.role.name == Role.SUPERVISOR:
            return base_qs.filter(user=user)

        if user.role.name == Role.UNIVERSITY_ADMIN:
            university = _get_university_admin_university(self.request)
            return base_qs.filter(university=university)

        return base_qs.none()


class SupervisorUpdateView(generics.UpdateAPIView):
    serializer_class = SupervisorUpdateSerializer
    permission_classes = [IsAuthenticated, IsSupervisor, IsOwnerOrReadOnly]

    def get_object(self):
        return get_object_or_404(SupervisorProfile, user=self.request.user)


# ============================================================
# UNIVERSITY ADMIN
# ============================================================
class UniversityAdminCreateView(generics.CreateAPIView):
    """
    IT Support creates University Admin users.
    IMPORTANT:
    - You MUST attach a university in a later step (or in another endpoint).
    - In this file we only create the user + profile.
    """
    serializer_class = UniversityAdminCreateSerializer
    permission_classes = [IsAuthenticated, IsTechSupport]

    def perform_create(self, serializer):
        user = serializer.save()
        # Profile is created but university must be set somewhere (universities app workflow)
        UniversityAdminProfile.objects.create(user=user)


class UniversityAdminListView(generics.ListAPIView):
    queryset = UniversityAdminProfile.objects.select_related("user", "university")
    serializer_class = UniversityAdminListSerializer
    permission_classes = [IsAuthenticated, IsTechSupport]


class UniversityAdminDetailView(generics.RetrieveAPIView):
    serializer_class = UniversityAdminDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base_qs = UniversityAdminProfile.objects.select_related("user", "university")

        if user.role.name == Role.UNIVERSITY_ADMIN:
            return base_qs.filter(user=user)

        if user.role.name == Role.TECH_SUPPORT:
            return base_qs

        return base_qs.none()


class UniversityAdminUpdateView(generics.UpdateAPIView):
    serializer_class = UniversityAdminUpdateSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin, IsOwnerOrReadOnly]

    def get_object(self):
        return get_object_or_404(UniversityAdminProfile, user=self.request.user)


# ============================================================
# TECH SUPPORT (SYSTEM)
# ============================================================
class TechSupportCreateView(generics.CreateAPIView):
    """
    🔐 Internal System API
    Only System Admin can create IT Support users
    (SystemAdmin = TechSupport with is_staff/is_superuser).
    """
    serializer_class = TechSupportCreateSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def perform_create(self, serializer):
        user = serializer.save()
        TechSupportProfile.objects.create(user=user)


class TechSupportListView(generics.ListAPIView):
    queryset = TechSupportProfile.objects.select_related("user")
    serializer_class = TechSupportListSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]


class TechSupportDetailView(generics.RetrieveAPIView):
    queryset = TechSupportProfile.objects.select_related("user")
    serializer_class = TechSupportDetailSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]


class TechSupportUpdateView(generics.UpdateAPIView):
    serializer_class = TechSupportUpdateSerializer
    permission_classes = [IsAuthenticated, IsTechSupport, IsOwnerOrReadOnly]

    def get_object(self):
        return get_object_or_404(TechSupportProfile, user=self.request.user)
