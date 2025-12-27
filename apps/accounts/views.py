# apps/accounts/views.py
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_audit_event
from .models import Role, PatientProfile, StudentProfile, SupervisorProfile, UniversityAdminProfile, TechSupportProfile
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

    def post(self, request):
        serializer = RoleBasedLoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.allowed_role = self.role_name
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        return Response(
            {
                "detail": "تم تسجيل الدخول بنجاح.",
                "user_id": user.id,
                "role": user.role.name,
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
    permission_classes = [CanCreateUniversityAdmin]


class TechSupportCreateView(generics.CreateAPIView):
    serializer_class = TechSupportCreateSerializer
    permission_classes = [CanCreateTechSupport]


# ============================================================
# SELF PROFILE
# ============================================================
class _BaseMeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticatedAndActive, IsSelfOnly]


class PatientMeView(_BaseMeView):
    serializer_class = PatientProfileSerializer

    def get_object(self):
        return PatientProfile.objects.select_related("user").get(user=self.request.user)


class StudentMeView(_BaseMeView):
    serializer_class = StudentProfileSerializer

    def get_object(self):
        return StudentProfile.objects.select_related("user", "university").get(
            user=self.request.user
        )


class SupervisorMeView(_BaseMeView):
    serializer_class = SupervisorProfileSerializer

    def get_object(self):
        return SupervisorProfile.objects.select_related("user", "university").get(
            user=self.request.user
        )


class UniversityAdminMeView(_BaseMeView):
    serializer_class = UniversityAdminProfileSerializer

    def get_object(self):
        return UniversityAdminProfile.objects.select_related("user", "university").get(
            user=self.request.user
        )


class TechSupportMeView(_BaseMeView):
    serializer_class = TechSupportProfileSerializer

    def get_object(self):
        return TechSupportProfile.objects.select_related("user").get(
            user=self.request.user
        )


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
