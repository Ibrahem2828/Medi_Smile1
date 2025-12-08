from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from .models import Report
from .serializers import ReportSerializer, ReportCreateSerializer, ReportUpdateSerializer
from apps.accounts.permissions import IsUniversityAdmin, IsTechSupport
from medismile.utils.auth import resolve_request_user, require_request_user


class ReportListView(generics.ListCreateAPIView):
    """API view for listing and creating reports."""
    
    serializer_class = ReportSerializer
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_queryset(self):
        """Get reports based on user role or provided filters."""
        user = resolve_request_user(self.request)
        student_id = self.request.query_params.get('student_id')
        university_id = self.request.query_params.get('university_id')
        report_type = self.request.query_params.get('report_type')
        is_active = self.request.query_params.get('is_active')
        
        queryset = Report.objects.all()
        
        if user:
            if user.role == 'student':
                queryset = queryset.filter(student=user)
            elif user.role == 'supervisor':
                # Supervisors can see reports of their students
                queryset = queryset.filter(student__studentprofile__university__supervisors=user)
            elif user.role in ['university_admin', 'tech_support']:
                # Admins can see all reports
                queryset = queryset.all()
            else:
                queryset = queryset.none()
        else:
            # If no user, allow filtering by explicit parameters
            if student_id:
                queryset = queryset.filter(student_id=student_id)
            if university_id:
                queryset = queryset.filter(university_id=university_id)
        
        # Additional filters
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == 'POST':
            return ReportCreateSerializer
        return ReportSerializer
    
    def perform_create(self, serializer):
        """Create a new report."""
        serializer.save()


class ReportDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API view for retrieving, updating and deleting a report."""
    
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method in ['PUT', 'PATCH']:
            return ReportUpdateSerializer
        return ReportSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def student_reports(request, student_id):
    """Get all reports for a specific student."""
    user, error = require_request_user(request, error_key='user_id')
    if error:
        return error
    
    # Check authorization
    from apps.accounts.models import User
    try:
        student = User.objects.get(id=student_id, role='student')
    except User.DoesNotExist:
        return Response({
            'error': _('Student not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Authorization check
    if user.role == 'student' and student != user:
        return Response({
            'error': _('You are not authorized to view this student\'s reports')
        }, status=status.HTTP_403_FORBIDDEN)
    
    reports = Report.objects.filter(student=student, is_active=True)
    serializer = ReportSerializer(reports, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def university_reports(request, university_id):
    """Get all reports for a specific university."""
    user, error = require_request_user(request, error_key='user_id')
    if error:
        return error
    
    # Check authorization
    if user.role not in ['university_admin', 'tech_support', 'supervisor']:
        return Response({
            'error': _('You are not authorized to view university reports')
        }, status=status.HTTP_403_FORBIDDEN)
    
    from apps.universities.models import University
    try:
        university = University.objects.get(id=university_id)
    except University.DoesNotExist:
        return Response({
            'error': _('University not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    reports = Report.objects.filter(university=university, is_active=True)
    serializer = ReportSerializer(reports, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


