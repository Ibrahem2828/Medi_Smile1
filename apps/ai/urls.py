# apps/ai/urls.py
from django.urls import path

from .views import (
    AIDiagnosisListView,
    AIDiagnosisDetailView,
    create_ai_diagnosis,
    review_ai_diagnosis_view,
    ai_health_view,
    my_ai_analysis,
)

app_name = "ai"

urlpatterns = [
    path("diagnoses/", AIDiagnosisListView.as_view(), name="ai-diagnosis-list"),
    path("diagnoses/<uuid:pk>/", AIDiagnosisDetailView.as_view(), name="ai-diagnosis-detail"),
    path("diagnose/", create_ai_diagnosis, name="ai-diagnose"),
    path("diagnoses/<uuid:pk>/review/", review_ai_diagnosis_view, name="ai-diagnosis-review"),
    path("health/", ai_health_view, name="ai-health"),
    path("my-analysis/", my_ai_analysis, name="ai-my-analysis"),
]
