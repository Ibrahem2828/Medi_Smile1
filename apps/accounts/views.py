# apps/accounts/views.py
from django.contrib.auth.models import update_last_login
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
    serializer_class = PatientCreateSerializer
    permission_classes = [AllowAny]


class PatientListView(generics.ListAPIView):
    queryset = PatientProfile.objects.select_related("user")
    serializer_class = PatientListSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin | IsTechSupport]


class PatientDetailView(generics.RetrieveAPIView):
    queryset = PatientProfile.objects.select_related("user")
    serializer_class = PatientDetailSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = "user__id"


class PatientUpdateView(generics.UpdateAPIView):
    serializer_class = PatientUpdateSerializer
    permission_classes = [IsAuthenticated, IsPatient, IsOwnerOrReadOnly]

    def get_object(self):
        return get_object_or_404(
            PatientProfile, user=self.request.user
        )


# ============================================================
# STUDENT
# ============================================================
class StudentCreateView(generics.CreateAPIView):
    serializer_class = StudentCreateSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]


class StudentListView(generics.ListAPIView):
    queryset = StudentProfile.objects.select_related("user", "university")
    serializer_class = StudentListSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]


class StudentDetailView(generics.RetrieveAPIView):
    queryset = StudentProfile.objects.select_related("user", "university")
    serializer_class = StudentDetailSerializer
    permission_classes = [IsAuthenticated]


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


class SupervisorListView(generics.ListAPIView):
    queryset = SupervisorProfile.objects.select_related("user", "university")
    serializer_class = SupervisorListSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]


class SupervisorDetailView(generics.RetrieveAPIView):
    queryset = SupervisorProfile.objects.select_related("user", "university")
    serializer_class = SupervisorDetailSerializer
    permission_classes = [IsAuthenticated]


class SupervisorUpdateView(generics.UpdateAPIView):
    serializer_class = SupervisorUpdateSerializer
    permission_classes = [IsAuthenticated, IsSupervisor, IsOwnerOrReadOnly]

    def get_object(self):
        return get_object_or_404(SupervisorProfile, user=self.request.user)


# ============================================================
# UNIVERSITY ADMIN
# ============================================================
class UniversityAdminCreateView(generics.CreateAPIView):
    serializer_class = UniversityAdminCreateSerializer
    permission_classes = [IsSystemAdmin]


class UniversityAdminListView(generics.ListAPIView):
    queryset = UniversityAdminProfile.objects.select_related("user", "university")
    serializer_class = UniversityAdminListSerializer
    permission_classes = [IsAuthenticated, IsTechSupport]


class UniversityAdminDetailView(generics.RetrieveAPIView):
    queryset = UniversityAdminProfile.objects.select_related("user", "university")
    serializer_class = UniversityAdminDetailSerializer
    permission_classes = [IsAuthenticated]


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
    """
    serializer_class = TechSupportCreateSerializer
    permission_classes = [IsSystemAdmin]


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
