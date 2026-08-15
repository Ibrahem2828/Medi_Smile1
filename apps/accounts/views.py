# apps/accounts/views.py
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import Http404

from apps.audit.services import log_audit_event
from .models import (
    Role,
    PatientProfile,
    StudentProfile,
    SupervisorProfile,
    UniversityAdminProfile,
    TechSupportProfile,
)
from .serializers import (
    RoleBasedLoginSerializer,
    PatientCreateSerializer,
    StudentCreateSerializer,
    SupervisorCreateSerializer,
    UniversityAdminCreateSerializer,
    TechSupportCreateSerializer,
    PatientProfileSerializer,
    StudentProfileSerializer,
    SupervisorProfileSerializer,
    UniversityAdminProfileSerializer,
    TechSupportProfileSerializer,
    FCMTokenSerializer,
)
from .permissions import (
    IsAuthenticatedAndActive,
    IsSelfOnly,
    IsUniversityAdmin,
    IsTechSupport,
    CanCreatePatient,
    CanCreateStudent,
    CanCreateSupervisor,
    CanCreateUniversityAdmin,
    CanCreateTechSupport,
)


# ============================================================
# ROLE-BASED LOGIN
# ============================================================
class BaseRoleLoginView(APIView):
    permission_classes = [AllowAny]
    role_name = None

    def _user_payload(self, user):
        return {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": getattr(user.role, "name", None),
            "role_id": str(user.role_id) if user.role_id else None,
            "fcm_token": user.fcm_token,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    def _token_payload(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

    def post(self, request):
        serializer = RoleBasedLoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.allowed_role = self.role_name
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        tokens = self._token_payload(user)
        user_data = self._user_payload(user)

        return Response(
            {
                "detail": "Login successful.",
                "tokens": tokens,
                "user": user_data,
            },
            status=status.HTTP_200_OK,
        )


class PatientLoginView(BaseRoleLoginView):
    role_name = Role.PATIENT


class StudentLoginView(BaseRoleLoginView):
    role_name = Role.STUDENT


class SupervisorLoginView(BaseRoleLoginView):
    role_name = Role.SUPERVISOR


class UniversityAdminLoginView(BaseRoleLoginView):
    role_name = Role.UNIVERSITY_ADMIN


class TechSupportLoginView(BaseRoleLoginView):
    role_name = Role.TECH_SUPPORT


# ============================================================
# USER CREATION
# ============================================================
class PatientRegisterView(generics.CreateAPIView):
    serializer_class = PatientCreateSerializer
    permission_classes = [CanCreatePatient]


class StudentCreateView(generics.CreateAPIView):
    serializer_class = StudentCreateSerializer
    permission_classes = [CanCreateStudent]


class SupervisorCreateView(generics.CreateAPIView):
    serializer_class = SupervisorCreateSerializer
    permission_classes = [CanCreateSupervisor]


class UniversityAdminCreateView(generics.CreateAPIView):
    serializer_class = UniversityAdminCreateSerializer
    permission_classes = [IsAuthenticatedAndActive, CanCreateUniversityAdmin]

    def create(self, request, *args, **kwargs):
        """
        Fail-safe creation:
        - اترك أخطاء الـ parsing/validation لتعود 400 من DRF تلقائياً.
        - تعامل مع الأعطال غير المتوقعة فقط.
        """
        try:
            return super().create(request, *args, **kwargs)
        except Exception as exc:  # pragma: no cover - defensive guard
            try:
                log_audit_event(
                    user=request.user,
                    action="accounts.university_admin.create.failed",
                    description=str(exc),
                )
            except Exception:
                pass
            return Response(
                {
                    "detail": "Failed to create university admin.",
                    "error": str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TechSupportCreateView(generics.CreateAPIView):
    serializer_class = TechSupportCreateSerializer
    permission_classes = [CanCreateTechSupport]


# ============================================================
# UNIVERSITY-SCOPED LISTING (ADMIN)
# ============================================================
class _BaseUniversityScopedListView(generics.ListAPIView):
    permission_classes = [IsAuthenticatedAndActive, IsUniversityAdmin]
    profile_model = None
    serializer_class = None

    def _get_university_id(self):
        profile = getattr(self.request.user, "universityadminprofile_profile", None)
        university_id = getattr(profile, "university_id", None)
        if not university_id:
            raise PermissionDenied("University Admin must belong to a university.")
        return university_id

    def get_queryset(self):
        university_id = self._get_university_id()
        base_qs = self.profile_model.objects.select_related("user")
        if hasattr(self.profile_model, "university"):
            base_qs = base_qs.select_related("university").filter(
                university_id=university_id
            )
        return base_qs.order_by("user__first_name", "user__last_name")


class UniversityStudentsListView(_BaseUniversityScopedListView):
    profile_model = StudentProfile
    serializer_class = StudentProfileSerializer


class UniversitySupervisorsListView(_BaseUniversityScopedListView):
    profile_model = SupervisorProfile
    serializer_class = SupervisorProfileSerializer


class UniversityAdminsListView(_BaseUniversityScopedListView):
    profile_model = UniversityAdminProfile
    serializer_class = UniversityAdminProfileSerializer


class UniversityAdminsByUniversityView(generics.ListAPIView):
    """
    Tech Support: list all university admins for a specific university (by query param).
    """

    permission_classes = [IsAuthenticatedAndActive, IsTechSupport]
    serializer_class = UniversityAdminProfileSerializer

    def get_queryset(self):
        university_id = self.request.query_params.get("university_id")
        if not university_id:
            raise PermissionDenied("university_id is required.")
        return (
            UniversityAdminProfile.objects.select_related("user", "university")
            .filter(university_id=university_id)
            .order_by("user__first_name", "user__last_name")
        )


class UniversityAdminsAllView(generics.ListAPIView):
    """
    Tech Support: list all university admins across all universities.
    """

    permission_classes = [IsAuthenticatedAndActive, IsTechSupport]
    serializer_class = UniversityAdminProfileSerializer

    def get_queryset(self):
        return (
            UniversityAdminProfile.objects.select_related("user", "university")
            .order_by("university__name", "user__first_name", "user__last_name")
        )


# ============================================================
# UNIVERSITY ADMIN MANAGED STUDENTS & SUPERVISORS (CRUD)
# ============================================================
class _UniversityScopeMixin:
    """
    Resolve university_id from the current University Admin profile.
    """

    def _get_admin_university_id(self):
        profile = getattr(self.request.user, "universityadminprofile_profile", None)
        university_id = getattr(profile, "university_id", None)
        if not university_id:
            raise PermissionDenied("University Admin must belong to a university.")
        return university_id


class UniversityAdminStudentsManageView(_UniversityScopeMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticatedAndActive, IsUniversityAdmin]

    def get_queryset(self):
        university_id = self._get_admin_university_id()
        return (
            StudentProfile.objects.select_related("user", "university")
            .filter(university_id=university_id)
            .order_by("user__first_name", "user__last_name")
        )

    def get_serializer_class(self):
        if self.request.method.lower() == "post":
            return StudentCreateSerializer
        return StudentProfileSerializer

    def perform_create(self, serializer):
        serializer.save()


class UniversityAdminStudentDetailView(_UniversityScopeMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticatedAndActive, IsUniversityAdmin]
    serializer_class = StudentProfileSerializer
    lookup_field = "user_id"

    def get_queryset(self):
        university_id = self._get_admin_university_id()
        return (
            StudentProfile.objects.select_related("user", "university")
            .filter(university_id=university_id)
        )


class UniversityAdminSupervisorsManageView(_UniversityScopeMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticatedAndActive, IsUniversityAdmin]

    def get_queryset(self):
        university_id = self._get_admin_university_id()
        return (
            SupervisorProfile.objects.select_related("user", "university")
            .filter(university_id=university_id)
            .order_by("user__first_name", "user__last_name")
        )

    def get_serializer_class(self):
        if self.request.method.lower() == "post":
            return SupervisorCreateSerializer
        return SupervisorProfileSerializer

    def perform_create(self, serializer):
        serializer.save()


class UniversityAdminSupervisorDetailView(_UniversityScopeMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticatedAndActive, IsUniversityAdmin]
    serializer_class = SupervisorProfileSerializer
    lookup_field = "user_id"

    def get_queryset(self):
        university_id = self._get_admin_university_id()
        return (
            SupervisorProfile.objects.select_related("user", "university")
            .filter(university_id=university_id)
        )


# ============================================================
# SELF PROFILE
# ============================================================
class _BaseMeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticatedAndActive, IsSelfOnly]

    def _get_profile_or_404(self, profile_model, *related_fields):
        try:
            return profile_model.objects.select_related(*related_fields).get(
                user=self.request.user
            )
        except profile_model.DoesNotExist as exc:
            raise Http404("Profile not found.") from exc


class PatientMeView(_BaseMeView):
    serializer_class = PatientProfileSerializer

    def get_object(self):
        return self._get_profile_or_404(PatientProfile, "user", "university")


class StudentMeView(_BaseMeView):
    serializer_class = StudentProfileSerializer

    def get_object(self):
        return self._get_profile_or_404(StudentProfile, "user", "university")


class SupervisorMeView(_BaseMeView):
    serializer_class = SupervisorProfileSerializer

    def get_object(self):
        return self._get_profile_or_404(SupervisorProfile, "user", "university")


class UniversityAdminMeView(_BaseMeView):
    serializer_class = UniversityAdminProfileSerializer

    def get_object(self):
        return self._get_profile_or_404(UniversityAdminProfile, "user", "university")


# ============================================================
# Tech Support: Manage University Admins (CRUD)
# ============================================================

class TechSupportUniversityAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Tech Support can retrieve/update/delete a University Admin.
    """

    queryset = UniversityAdminProfile.objects.select_related("user", "university")
    serializer_class = UniversityAdminProfileSerializer
    permission_classes = [IsAuthenticatedAndActive, IsTechSupport]
    lookup_field = "user_id"

    def perform_destroy(self, instance):
        # Soft-delete the user (deactivate) to preserve history
        user = instance.user
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])
        instance.delete()


class TechSupportMeView(_BaseMeView):
    serializer_class = TechSupportProfileSerializer

    def get_object(self):
        return self._get_profile_or_404(TechSupportProfile, "user")


# ============================================================
# FCM Token Register/Rotate
# ============================================================
class FCMTokenView(APIView):
    permission_classes = [IsAuthenticatedAndActive]

    def post(self, request):
        serializer = FCMTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["fcm_token"]
        request.user.fcm_token = token
        request.user.save(update_fields=["fcm_token", "updated_at"])

        log_audit_event(
            user=request.user,
            university=getattr(request.user, "universityadminprofile_profile", None)
            and request.user.universityadminprofile_profile.university,
            action="accounts.fcm_token.registered",
            description="FCM token registered/rotated",
            metadata={"token_present": bool(token)},
        )

        return Response({"detail": "Token registered."}, status=status.HTTP_200_OK)

    def delete(self, request):
        request.user.fcm_token = None
        request.user.save(update_fields=["fcm_token", "updated_at"])

        log_audit_event(
            user=request.user,
            university=getattr(request.user, "universityadminprofile_profile", None)
            and request.user.universityadminprofile_profile.university,
            action="accounts.fcm_token.removed",
            description="FCM token removed",
        )

        return Response({"detail": "Token removed."}, status=status.HTTP_200_OK)
