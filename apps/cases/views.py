from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from rest_framework import serializers
from apps.accounts.models import User
from .models import Case, CaseHistory, CaseAssignmentRequest
from .serializers import (
    CaseSerializer, CaseCreateSerializer, CaseUpdateSerializer,
    CaseAssignmentRequestSerializer, CaseAssignmentRequestCreateSerializer,
    CaseAssignmentRequestUpdateSerializer
)
from apps.accounts.permissions import IsPatient, IsStudent, IsSupervisor
from medismile.utils.permissions import RoleBasedPermission


class CaseListView(generics.ListCreateAPIView):
    """API view for listing and creating cases."""
    
    serializer_class = CaseSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_queryset(self):
        """Get cases based on user role."""
        user = self.request.user
        
        if user.role == 'patient':
            return Case.objects.filter(patient=user)
        elif user.role == 'student':
            return Case.objects.filter(student=user) | Case.objects.filter(is_public=True)
        elif user.role == 'supervisor':
            return Case.objects.filter(supervisor=user)
        elif user.role in ['university_admin', 'tech_support']:
            return Case.objects.all()
        
        return Case.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == 'POST':
            return CaseCreateSerializer
        return CaseSerializer
    
    def perform_create(self, serializer):
        """Create a new case and add to history."""
        with transaction.atomic():
            case = serializer.save()
            
            # Add to history
            CaseHistory.objects.create(
                case=case,
                action='created',
                description=f"Case '{case.title}' was created",
                performed_by=self.request.user
            )


class CaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API view for retrieving, updating and deleting a case."""
    
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_permissions(self):
        """Get permissions based on request method."""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            # return [permissions.IsAuthenticated(), IsPatient()]  # معلق مؤقتاً
            return [AllowAny()]  # مؤقتاً للسماح بالوصول بدون مصادقة
        # return [permissions.IsAuthenticated()]  # معلق مؤقتاً
        return [AllowAny()]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def perform_update(self, serializer):
        """Update a case and add to history."""
        with transaction.atomic():
            old_case = Case.objects.get(pk=self.get_object().pk)
            case = serializer.save()
            
            # Add to history if status changed
            if old_case.status != case.status:
                CaseHistory.objects.create(
                    case=case,
                    action='status_changed',
                    description=f"Case status changed from '{old_case.status}' to '{case.status}'",
                    performed_by=self.request.user
                )
            else:
                CaseHistory.objects.create(
                    case=case,
                    action='updated',
                    description=f"Case '{case.title}' was updated",
                    performed_by=self.request.user
                )


class CaseAssignmentRequestListView(generics.ListCreateAPIView):
    """API view for listing and creating case assignment requests."""
    
    serializer_class = CaseAssignmentRequestSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_queryset(self):
        """Get assignment requests based on user role."""
        user = self.request.user
        case_id = self.kwargs.get('case_id')
        
        if user.role == 'student':
            return CaseAssignmentRequest.objects.filter(student=user, case_id=case_id)
        elif user.role == 'supervisor':
            return CaseAssignmentRequest.objects.filter(case__supervisor=user, case_id=case_id)
        elif user.role in ['university_admin', 'tech_support']:
            return CaseAssignmentRequest.objects.filter(case_id=case_id)
        
        return CaseAssignmentRequest.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == 'POST':
            return CaseAssignmentRequestCreateSerializer
        return CaseAssignmentRequestSerializer
    
    def perform_create(self, serializer):
        """Create a new case assignment request."""
        case_id = self.kwargs.get('case_id')
        case = Case.objects.get(id=case_id)
        
        # Check if case is open
        if case.status != 'open':
            raise serializers.ValidationError(("Case is not open for assignment"))
        
        serializer.save(case=case)


class CaseAssignmentRequestDetailView(generics.RetrieveUpdateAPIView):
    """API view for retrieving and updating a case assignment request."""
    
    queryset = CaseAssignmentRequest.objects.all()
    serializer_class = CaseAssignmentRequestSerializer
    # permission_classes = [permissions.IsAuthenticated, IsSupervisor]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method in ['PUT', 'PATCH']:
            return CaseAssignmentRequestUpdateSerializer
        return CaseAssignmentRequestSerializer
    
    def perform_update(self, serializer):
        """Update a case assignment request and update case if accepted."""
        with transaction.atomic():
            assignment_request = serializer.save()
            
            # If request is accepted, assign student to case
            if assignment_request.status == 'accepted':
                case = assignment_request.case
                case.student = assignment_request.student
                case.status = 'assigned'
                case.save()
                
                # Add to case history
                CaseHistory.objects.create(
                    case=case,
                    action='assigned',
                    description=f"Case assigned to student '{assignment_request.student.username}'",
                    performed_by=self.request.user
                )


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated, IsStudent])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def request_case_assignment(request, case_id):
    """Request assignment to a case."""
    try:
        case = Case.objects.get(id=case_id)
    except Case.DoesNotExist:
        return Response({
            'error': _('Case not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if case is open
    if case.status != 'open':
        return Response({
            'error': _('Case is not open for assignment')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if request already exists
    if CaseAssignmentRequest.objects.filter(case=case, student=request.user).exists():
        return Response({
            'error': _('Assignment request already exists')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create assignment request
    assignment_request = CaseAssignmentRequest.objects.create(
        case=case,
        student=request.user,
        message=request.data.get('message', '')
    )
    
    serializer = CaseAssignmentRequestSerializer(assignment_request)
    return Response({
        'message': _('Assignment request created successfully'),
        'assignment_request': serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated, IsSupervisor])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def supervisor_case_action(request, case_id):
    """Supervisor action on a case (accept/reject student assignment)."""
    try:
        case = Case.objects.get(id=case_id)
    except Case.DoesNotExist:
        return Response({
            'error': _('Case not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if supervisor is assigned to the case
    if case.supervisor != request.user:
        return Response({
            'error': _('You are not assigned as supervisor to this case')
        }, status=status.HTTP_403_FORBIDDEN)
    
    action = request.data.get('action')
    student_id = request.data.get('student_id')
    response_message = request.data.get('message', '')
    
    if action not in ['accept', 'reject']:
        return Response({
            'error': _('Invalid action')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        student = User.objects.get(id=student_id, role='student')
    except User.DoesNotExist:
        return Response({
            'error': _('Student not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get assignment request
    try:
        assignment_request = CaseAssignmentRequest.objects.get(case=case, student=student)
    except CaseAssignmentRequest.DoesNotExist:
        return Response({
            'error': _('Assignment request not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    with transaction.atomic():
        if action == 'accept':
            # Assign student to case
            case.student = student
            case.status = 'assigned'
            case.save()
            
            # Update assignment request
            assignment_request.status = 'accepted'
            assignment_request.supervisor_response = response_message
            assignment_request.save()
            
            # Add to case history
            CaseHistory.objects.create(
                case=case,
                action='assigned',
                description=f"Case assigned to student '{student.username}'",
                performed_by=request.user
            )
            
            return Response({
                'message': _('Student assigned to case successfully')
            }, status=status.HTTP_200_OK)
        
        elif action == 'reject':
            # Update assignment request
            assignment_request.status = 'rejected'
            assignment_request.supervisor_response = response_message
            assignment_request.save()
            
            return Response({
                'message': _('Assignment request rejected')
            }, status=status.HTTP_200_OK)