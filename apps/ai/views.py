# apps/ai/views.py
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import AIDiagnosis
from .serializers import AIDiagnosisSerializer, AIDiagnosisRequestSerializer
from .selectors import get_ai_diagnosis_queryset_for_user
from .permissions import CanRequestAIDiagnosis, CanAccessAIDiagnosis
from .services import request_ai_diagnosis


class AIDiagnosisListView(generics.ListAPIView):
    serializer_class = AIDiagnosisSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return get_ai_diagnosis_queryset_for_user(user=self.request.user)


class AIDiagnosisDetailView(generics.RetrieveAPIView):
    serializer_class = AIDiagnosisSerializer
    permission_classes = [IsAuthenticated, CanAccessAIDiagnosis]

    def get_queryset(self):
        return get_ai_diagnosis_queryset_for_user(user=self.request.user)


@api_view(["POST"])
@permission_classes([IsAuthenticated, CanRequestAIDiagnosis])
def create_ai_diagnosis(request):
    serializer = AIDiagnosisRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    diagnosis = request_ai_diagnosis(
        actor=request.user,
        case_id=serializer.validated_data["case_id"],
        symptoms_text=serializer.validated_data["symptoms_text"],
        image_urls=serializer.validated_data.get("image_urls") or [],
    )

    return Response(
        {"diagnosis": AIDiagnosisSerializer(diagnosis).data},
        status=status.HTTP_201_CREATED,
    )
