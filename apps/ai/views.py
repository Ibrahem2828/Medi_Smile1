from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from .models import AIDiagnosis
from .serializers import AIDiagnosisSerializer, AIRequestSerializer
from .services import AIService
from apps.accounts.permissions import IsPatient
from apps.cases.models import Case


class AIDiagnosisListView(generics.ListAPIView):
    """API view for listing AI diagnoses."""
    
    serializer_class = AIDiagnosisSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get AI diagnoses based on user role."""
        user = self.request.user
        
        if user.role == 'patient':
            return AIDiagnosis.objects.filter(patient=user)
        elif user.role == 'student':
            # Get cases assigned to student
            case_ids = Case.objects.filter(student=user).values_list('id', flat=True)
            return AIDiagnosis.objects.filter(case_id__in=case_ids)
        elif user.role == 'supervisor':
            # Get cases supervised by supervisor
            case_ids = Case.objects.filter(supervisor=user).values_list('id', flat=True)
            return AIDiagnosis.objects.filter(case_id__in=case_ids)
        elif user.role in ['university_admin', 'tech_support']:
            return AIDiagnosis.objects.all()
        
        return AIDiagnosis.objects.none()


class AIDiagnosisDetailView(generics.RetrieveAPIView):
    """API view for retrieving an AI diagnosis."""
    
    queryset = AIDiagnosis.objects.all()
    serializer_class = AIDiagnosisSerializer
    permission_classes = [IsAuthenticated]


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsPatient])
def analyze_symptoms(request):
    """Analyze symptoms using AI."""
    serializer = AIRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    symptoms = serializer.validated_data['symptoms']
    case_id = serializer.validated_data.get('case_id')
    
    # Get case if provided
    case = None
    if case_id:
        try:
            case = Case.objects.get(id=case_id, patient=request.user)
        except Case.DoesNotExist:
            return Response({
                'error': _('Case not found')
            }, status=status.HTTP_404_NOT_FOUND)
    
    # Create AI diagnosis
    ai_diagnosis = AIService.create_ai_diagnosis(
        patient=request.user,
        symptoms=symptoms,
        case=case
    )
    
    # Serialize and return
    diagnosis_serializer = AIDiagnosisSerializer(ai_diagnosis)
    return Response({
        'message': _('Symptoms analyzed successfully'),
        'diagnosis': diagnosis_serializer.data
    }, status=status.HTTP_201_CREATED)