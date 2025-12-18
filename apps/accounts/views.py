from rest_framework import generics, status, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import update_last_login
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from .models import (
    PatientProfile, StudentProfile, SupervisorProfile,
    UniversityAdminProfile, TechSupportProfile, User
)
from .serializers import (
    PatientListSerializer, PatientDetailSerializer, PatientCreateSerializer, PatientUpdateSerializer,
    StudentListSerializer, StudentDetailSerializer, StudentCreateSerializer, StudentUpdateSerializer,
    SupervisorListSerializer, SupervisorDetailSerializer, SupervisorCreateSerializer, SupervisorUpdateSerializer,
    UniversityAdminListSerializer, UniversityAdminDetailSerializer, UniversityAdminCreateSerializer, UniversityAdminUpdateSerializer,
    TechSupportListSerializer, TechSupportDetailSerializer, TechSupportCreateSerializer, TechSupportUpdateSerializer,
    LoginSerializer, LogoutSerializer, UserSerializer
)
from .permissions import IsPatient, IsStudent, IsSupervisor, IsUniversityAdmin, IsTechSupport

class APIResponse:
    """Standardized API response format."""
    
    @staticmethod
    def success(message, data=None, status_code=status.HTTP_200_OK):
        return Response({
            "status": "success",
            "message": message,
            "data": data
        }, status=status_code)
    
    @staticmethod
    def error(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({
            "status": "error",
            "message": message,
            "errors": errors
        }, status=status_code)

# ==================== AUTHENTICATION VIEWS ==================== #

class LoginView(APIView):
    """API view to authenticate users and return JWT tokens."""
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={'request': request})

        if not serializer.is_valid():
            return APIResponse.error("فشل تسجيل الدخول.", serializer.errors, status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        update_last_login(None, user)

        data = {
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            },
            "user": UserSerializer(user).data
        }

        return APIResponse.success("تم تسجيل الدخول بنجاح.", data, status.HTTP_200_OK)

class LogoutView(APIView):
    """API view to blacklist refresh token and log the user out."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = LogoutSerializer(data=request.data)

        if not serializer.is_valid():
            return APIResponse.error("فشل تسجيل الخروج.", serializer.errors, status.HTTP_400_BAD_REQUEST)

        refresh_token = serializer.validated_data['refresh_token']

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return APIResponse.error("رمز التحديث غير صالح أو منتهي.", status_code=status.HTTP_400_BAD_REQUEST)

        return APIResponse.success("تم تسجيل الخروج بنجاح.", status_code=status.HTTP_205_RESET_CONTENT)

# ==================== PATIENT VIEWS ==================== #

class PatientListView(generics.ListAPIView):
    """API view to list all patients."""
    queryset = PatientProfile.objects.select_related('user').all()
    serializer_class = PatientListSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success("تم جلب قائمة المرضى بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("فشل جلب قائمة المرضى.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class PatientCreateView(generics.CreateAPIView):
    """API view to create a new patient."""
    serializer_class = PatientCreateSerializer
    permission_classes = [AllowAny]  # Register is public
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Get the created profile
            profile = PatientProfile.objects.get(user=user)
            return APIResponse.success(
                "تم إنشاء المريض بنجاح.",
                PatientDetailSerializer(profile).data,
                status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return APIResponse.error("بيانات المريض غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل إنشاء المريض.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class PatientDetailView(generics.RetrieveAPIView):
    """API view to retrieve patient details."""
    queryset = PatientProfile.objects.select_related('user')
    serializer_class = PatientDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success("تم جلب بيانات المريض بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("المريض غير موجود.", str(e), status.HTTP_404_NOT_FOUND)

class PatientUpdateView(generics.UpdateAPIView):
    """API view to update patient details."""
    serializer_class = PatientUpdateSerializer
    permission_classes = [IsAuthenticated, IsPatient]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id, role='patient')
        return get_object_or_404(PatientProfile, user=user)
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return APIResponse.success("تم تحديث بيانات المريض بنجاح.", serializer.data)
        except ValidationError as e:
            return APIResponse.error("بيانات التحديث غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل تحديث بيانات المريض.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class PatientDeleteView(generics.DestroyAPIView):
    """API view to delete a patient."""
    permission_classes = [IsAuthenticated, IsPatient]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id, role='patient')
        return get_object_or_404(PatientProfile, user=user)
    
    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = instance.user
            instance.delete()
            user.delete()
            return APIResponse.success("تم حذف المريض بنجاح.")
        except Exception as e:
            return APIResponse.error("فشل حذف المريض.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== STUDENT VIEWS ==================== #

class StudentListView(generics.ListAPIView):
    """API view to list all students."""
    queryset = StudentProfile.objects.select_related('user', 'university').all()
    serializer_class = StudentListSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success("تم جلب قائمة الطلاب بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("فشل جلب قائمة الطلاب.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class StudentCreateView(generics.CreateAPIView):
    """API view to create a new student."""
    serializer_class = StudentCreateSerializer
    permission_classes = [AllowAny]  # Register is public
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Get the created profile
            profile = StudentProfile.objects.get(user=user)
            return APIResponse.success(
                "تم إنشاء الطالب بنجاح.",
                StudentDetailSerializer(profile).data,
                status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return APIResponse.error("بيانات الطالب غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل إنشاء الطالب.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class StudentDetailView(generics.RetrieveAPIView):
    """API view to retrieve student details."""
    queryset = StudentProfile.objects.select_related('user', 'university')
    serializer_class = StudentDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success("تم جلب بيانات الطالب بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("الطالب غير موجود.", str(e), status.HTTP_404_NOT_FOUND)

class StudentUpdateView(generics.UpdateAPIView):
    """API view to update student details."""
    serializer_class = StudentUpdateSerializer
    permission_classes = [IsAuthenticated, IsStudent]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id, role='student')
        return get_object_or_404(StudentProfile, user=user)
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return APIResponse.success("تم تحديث بيانات الطالب بنجاح.", serializer.data)
        except ValidationError as e:
            return APIResponse.error("بيانات التحديث غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل تحديث بيانات الطالب.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class StudentDeleteView(generics.DestroyAPIView):
    """API view to delete a student."""
    permission_classes = [IsAuthenticated, IsStudent]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id, role='student')
        return get_object_or_404(StudentProfile, user=user)
    
    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = instance.user
            instance.delete()
            user.delete()
            return APIResponse.success("تم حذف الطالب بنجاح.")
        except Exception as e:
            return APIResponse.error("فشل حذف الطالب.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== SUPERVISOR VIEWS ==================== #

class SupervisorListView(generics.ListAPIView):
    """API view to list all supervisors."""
    queryset = SupervisorProfile.objects.select_related('user', 'university').all()
    serializer_class = SupervisorListSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success("تم جلب قائمة المشرفين بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("فشل جلب قائمة المشرفين.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class SupervisorCreateView(generics.CreateAPIView):
    """API view to create a new supervisor."""
    serializer_class = SupervisorCreateSerializer
    permission_classes = [AllowAny]  # Register is public
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Get the created profile
            profile = SupervisorProfile.objects.get(user=user)
            return APIResponse.success(
                "تم إنشاء المشرف بنجاح.",
                SupervisorDetailSerializer(profile).data,
                status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return APIResponse.error("بيانات المشرف غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل إنشاء المشرف.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class SupervisorDetailView(generics.RetrieveAPIView):
    """API view to retrieve supervisor details."""
    queryset = SupervisorProfile.objects.select_related('user', 'university')
    serializer_class = SupervisorDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success("تم جلب بيانات المشرف بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("المشرف غير موجود.", str(e), status.HTTP_404_NOT_FOUND)

class SupervisorUpdateView(generics.UpdateAPIView):
    """API view to update supervisor details."""
    serializer_class = SupervisorUpdateSerializer
    permission_classes = [IsAuthenticated, IsSupervisor]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id, role='supervisor')
        return get_object_or_404(SupervisorProfile, user=user)
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return APIResponse.success("تم تحديث بيانات المشرف بنجاح.", serializer.data)
        except ValidationError as e:
            return APIResponse.error("بيانات التحديث غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل تحديث بيانات المشرف.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class SupervisorDeleteView(generics.DestroyAPIView):
    """API view to delete a supervisor."""
    permission_classes = [IsAuthenticated, IsSupervisor]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id, role='supervisor')
        return get_object_or_404(SupervisorProfile, user=user)
    
    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = instance.user
            instance.delete()
            user.delete()
            return APIResponse.success("تم حذف المشرف بنجاح.")
        except Exception as e:
            return APIResponse.error("فشل حذف المشرف.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== UNIVERSITY ADMIN VIEWS ==================== #

class UniversityAdminListView(generics.ListAPIView):
    """API view to list all university admins."""
    queryset = UniversityAdminProfile.objects.select_related('user', 'university').all()
    serializer_class = UniversityAdminListSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success("تم جلب قائمة مسؤولي الجامعة بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("فشل جلب قائمة مسؤولي الجامعة.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class UniversityAdminCreateView(generics.CreateAPIView):
    """API view to create a new university admin."""
    serializer_class = UniversityAdminCreateSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Get the created profile
            profile = UniversityAdminProfile.objects.get(user=user)
            return APIResponse.success(
                "تم إنشاء مسؤول الجامعة بنجاح.",
                UniversityAdminDetailSerializer(profile).data,
                status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return APIResponse.error("بيانات مسؤول الجامعة غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل إنشاء مسؤول الجامعة.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class UniversityAdminDetailView(generics.RetrieveAPIView):
    """API view to retrieve university admin details."""
    queryset = UniversityAdminProfile.objects.select_related('user', 'university')
    serializer_class = UniversityAdminDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success("تم جلب بيانات مسؤول الجامعة بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("مسؤول الجامعة غير موجود.", str(e), status.HTTP_404_NOT_FOUND)

class UniversityAdminUpdateView(generics.UpdateAPIView):
    """API view to update university admin details."""
    serializer_class = UniversityAdminUpdateSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id, role='university_admin')
        return get_object_or_404(UniversityAdminProfile, user=user)
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return APIResponse.success("تم تحديث بيانات مسؤول الجامعة بنجاح.", serializer.data)
        except ValidationError as e:
            return APIResponse.error("بيانات التحديث غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل تحديث بيانات مسؤول الجامعة.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class UniversityAdminDeleteView(generics.DestroyAPIView):
    """API view to delete a university admin."""
    permission_classes = [IsAuthenticated, IsUniversityAdmin]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id, role='university_admin')
        return get_object_or_404(UniversityAdminProfile, user=user)
    
    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = instance.user
            instance.delete()
            user.delete()
            return APIResponse.success("تم حذف مسؤول الجامعة بنجاح.")
        except Exception as e:
            return APIResponse.error("فشل حذف مسؤول الجامعة.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== TECH SUPPORT VIEWS ==================== #

class TechSupportListView(generics.ListAPIView):
    """API view to list all tech support."""
    queryset = TechSupportProfile.objects.select_related('user').all()
    serializer_class = TechSupportListSerializer
    permission_classes = [IsAuthenticated, IsTechSupport]
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success("تم جلب قائمة الدعم الفني بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("فشل جلب قائمة الدعم الفني.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class TechSupportCreateView(generics.CreateAPIView):
    """API view to create a new tech support."""
    serializer_class = TechSupportCreateSerializer
    permission_classes = [IsAuthenticated, IsTechSupport]
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            
            # Get the created profile
            profile = TechSupportProfile.objects.get(user=user)
            return APIResponse.success(
                "تم إنشاء الدعم الفني بنجاح.",
                TechSupportDetailSerializer(profile).data,
                status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return APIResponse.error("بيانات الدعم الفني غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل إنشاء الدعم الفني.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class TechSupportDetailView(generics.RetrieveAPIView):
    """API view to retrieve tech support details."""
    queryset = TechSupportProfile.objects.select_related('user')
    serializer_class = TechSupportDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success("تم جلب بيانات الدعم الفني بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("الدعم الفني غير موجود.", str(e), status.HTTP_404_NOT_FOUND)

class TechSupportUpdateView(generics.UpdateAPIView):
    """API view to update tech support details."""
    serializer_class = TechSupportUpdateSerializer
    permission_classes = [IsAuthenticated, IsTechSupport]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id, role='tech_support')
        return get_object_or_404(TechSupportProfile, user=user)
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return APIResponse.success("تم تحديث بيانات الدعم الفني بنجاح.", serializer.data)
        except ValidationError as e:
            return APIResponse.error("بيانات التحديث غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل تحديث بيانات الدعم الفني.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

class TechSupportDeleteView(generics.DestroyAPIView):
    """API view to delete a tech support."""
    permission_classes = [IsAuthenticated, IsTechSupport]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(User, id=user_id, role='tech_support')
        return get_object_or_404(TechSupportProfile, user=user)
    
    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = instance.user
            instance.delete()
            user.delete()
            return APIResponse.success("تم حذف الدعم الفني بنجاح.")
        except Exception as e:
            return APIResponse.error("فشل حذف الدعم الفني.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)