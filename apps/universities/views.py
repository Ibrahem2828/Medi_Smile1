from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from .models import University, Course
from .serializers import (
    UniversityListSerializer, UniversityDetailSerializer, UniversityCreateSerializer,
    CourseListSerializer, CourseDetailSerializer, CourseCreateSerializer
)
from apps.accounts.permissions import IsUniversityAdmin


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


# ==================== UNIVERSITY VIEWS ==================== #

class UniversityListView(generics.ListAPIView):
    """API view to list all universities."""
    queryset = University.objects.filter(is_active=True)
    serializer_class = UniversityListSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success("تم جلب قائمة الجامعات بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("فشل جلب قائمة الجامعات.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class UniversityCreateView(generics.CreateAPIView):
    """API view to create a new university."""
    serializer_class = UniversityCreateSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            university = serializer.save()
            return APIResponse.success(
                "تم إنشاء الجامعة بنجاح.",
                UniversityDetailSerializer(university).data,
                status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return APIResponse.error("بيانات الجامعة غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل إنشاء الجامعة.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class UniversityDetailView(generics.RetrieveAPIView):
    """API view to retrieve university details."""
    queryset = University.objects.all()
    serializer_class = UniversityDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success("تم جلب بيانات الجامعة بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("الجامعة غير موجودة أو حدث خطأ.", str(e), status.HTTP_404_NOT_FOUND)


class UniversityUpdateView(generics.UpdateAPIView):
    """API view to update university details."""
    queryset = University.objects.all()
    serializer_class = UniversityDetailSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]
    lookup_field = 'pk'
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return APIResponse.success("تم تحديث بيانات الجامعة بنجاح.", serializer.data)
        except ValidationError as e:
            return APIResponse.error("بيانات التحديث غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل تحديث بيانات الجامعة.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class UniversityDeleteView(generics.DestroyAPIView):
    """API view to delete a university."""
    queryset = University.objects.all()
    permission_classes = [IsAuthenticated, IsUniversityAdmin]
    lookup_field = 'pk'
    
    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.is_active = False
            instance.save()
            return APIResponse.success("تم حذف الجامعة بنجاح.")
        except Exception as e:
            return APIResponse.error("فشل حذف الجامعة.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== COURSE VIEWS ==================== #

class UniversityCoursesView(generics.ListAPIView):
    """API view to list courses for a specific university."""
    serializer_class = CourseListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get courses for the specified university."""
        university_id = self.kwargs.get('university_id')
        return Course.objects.filter(university_id=university_id, is_active=True)
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success("تم جلب قائمة الكورسات بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("فشل جلب قائمة الكورسات.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


# في ملف views.py (ضمن قسم COURSE VIEWS)

class CourseCreateView(generics.CreateAPIView):
    """API view to create a new course."""
    queryset = Course.objects.all()
    serializer_class = CourseCreateSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]
    
    def create(self, request, *args, **kwargs):
        try:
            # 1. استخراج university_id من مسار الـ URL
            university_id = kwargs.get('university_id')
            
            # 2. إنشاء نسخة قابلة للتعديل من بيانات الطلب
            data = request.data.copy()
            
            # 3. إضافة university_id إلى البيانات تحت اسم الحقل 'university'
            # هذا يطابق اسم الـ ForeignKey في models.py
            data['university'] = university_id 
            
            # 4. تمرير البيانات المعدلة إلى الـ Serializer
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            
            # 5. حفظ الكورس الجديد (مع ربطه بالجامعة)
            serializer.save()
            
            return APIResponse.success("تم إنشاء الكورس بنجاح.", serializer.data, status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return APIResponse.error("بيانات الإنشاء غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # هذا السطر ضروري لالتقاط أي خطأ آخر وإرجاع 500 موضح
            return APIResponse.error("فشل إنشاء الكورس.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)



class CourseDetailView(generics.RetrieveAPIView):
    """API view to retrieve course details."""
    queryset = Course.objects.all()
    serializer_class = CourseDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success("تم جلب بيانات الكورس بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("الكورس غير موجود أو حدث خطأ.", str(e), status.HTTP_404_NOT_FOUND)


class CourseUpdateView(generics.UpdateAPIView):
    """API view to update course details."""
    queryset = Course.objects.all()
    serializer_class = CourseDetailSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin]
    lookup_field = 'pk'
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return APIResponse.success("تم تحديث بيانات الكورس بنجاح.", serializer.data)
        except ValidationError as e:
            return APIResponse.error("بيانات التحديث غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل تحديث بيانات الكورس.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseDeleteView(generics.DestroyAPIView):
    """API view to delete a course."""
    queryset = Course.objects.all()
    permission_classes = [IsAuthenticated, IsUniversityAdmin]
    lookup_field = 'pk'
    
    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.is_active = False
            instance.save()
            return APIResponse.success("تم حذف الكورس بنجاح.")
        except Exception as e:
            return APIResponse.error("فشل حذف الكورس.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)