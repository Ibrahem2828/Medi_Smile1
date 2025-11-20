from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django.db.models import Avg
from .models import Evaluation
from .serializers import EvaluationSerializer, EvaluationCreateSerializer
from apps.accounts.permissions import IsPatient, IsStudent, IsSupervisor

from rest_framework import serializers
class EvaluationListView(generics.ListCreateAPIView):
    """API view for listing and creating evaluations."""
    
    serializer_class = EvaluationSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_queryset(self):
        """Get evaluations based on user role and business rules."""
        user = self.request.user
        evaluator_type = self.request.query_params.get('evaluator_type')
        student_id = self.request.query_params.get('student_id')
        patient_id = self.request.query_params.get('patient_id')
        appointment_id = self.request.query_params.get('appointment_id')
        
        evaluations = Evaluation.objects.all()
        
        # Filter by role-based visibility
        if user.role == 'patient':
            # Patients can see evaluations they made or evaluations about them (but no one evaluates patients)
            evaluations = evaluations.filter(patient=user)
        elif user.role == 'student':
            # Students can see evaluations they received (they are evaluated)
            evaluations = evaluations.filter(student=user)
        elif user.role == 'supervisor':
            # Supervisors can see evaluations they made (evaluating students)
            evaluations = evaluations.filter(evaluator_type='supervisor')
        elif user.role == 'university_admin':
            # University admins can see all evaluations
            evaluations = Evaluation.objects.all()
        elif user.role == 'tech_support':
            # Tech support can see all evaluations
            evaluations = Evaluation.objects.all()
        else:
            evaluations = Evaluation.objects.none()
        
        # Additional filters
        if evaluator_type:
            evaluations = evaluations.filter(evaluator_type=evaluator_type)
        if student_id:
            evaluations = evaluations.filter(student_id=student_id)
        if patient_id:
            evaluations = evaluations.filter(patient_id=patient_id)
        if appointment_id:
            evaluations = evaluations.filter(appointment_id=appointment_id)
        
        return evaluations.distinct()
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == 'POST':
            return EvaluationCreateSerializer
        return EvaluationSerializer
    
    def perform_create(self, serializer):
        """Create a new evaluation with automatic evaluator type assignment."""
        user = self.request.user
        
        # Automatically set evaluator_type based on user role if not provided
        if 'evaluator_type' not in serializer.validated_data:
            role_to_evaluator_type = {
                'patient': 'patient',
                'supervisor': 'supervisor',
                'student': 'student',
                'university_admin': 'university',
            }
            evaluator_type = role_to_evaluator_type.get(user.role)
            if evaluator_type:
                serializer.validated_data['evaluator_type'] = evaluator_type
        
        serializer.save()


class EvaluationDetailView(generics.RetrieveAPIView):
    """API view for retrieving an evaluation."""
    
    queryset = Evaluation.objects.all()
    serializer_class = EvaluationSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة


@api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def student_average_ratings(request, student_id):
    """Get average ratings for a student."""
    try:
        from apps.accounts.models import User
        student = User.objects.get(id=student_id, role='student')
    except User.DoesNotExist:
        return Response({
            'error': _('Student not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get average ratings for the student
    evaluations = Evaluation.objects.filter(student=student)
    
    if not evaluations.exists():
        return Response({
            'message': _('No evaluations found for this student'),
            'average_rating': None,
            'total_evaluations': 0
        }, status=status.HTTP_200_OK)
    
    # Calculate average rating
    avg_rating = evaluations.aggregate(avg=Avg('rating'))['avg']
    
    # Group by evaluator type
    by_type = {}
    for eval_type, _ in Evaluation.EVALUATOR_TYPE_CHOICES:
        type_evaluations = evaluations.filter(evaluator_type=eval_type)
        if type_evaluations.exists():
            by_type[eval_type] = {
                'average': round(type_evaluations.aggregate(avg=Avg('rating'))['avg'], 2),
                'count': type_evaluations.count()
            }
    
    return Response({
        'student_id': str(student.id),
        'student_username': student.username,
        'average_rating': round(avg_rating, 2) if avg_rating else None,
        'total_evaluations': evaluations.count(),
        'by_evaluator_type': by_type
    }, status=status.HTTP_200_OK)