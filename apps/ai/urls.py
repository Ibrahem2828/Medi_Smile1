# apps/ai/urls.py
from django.urls import path

from .views import (
    AIDiagnosisListView,
    AIDiagnosisDetailView,
    create_ai_diagnosis,
)

app_name = "ai"

urlpatterns = [
    path("diagnoses/", AIDiagnosisListView.as_view(), name="ai-diagnosis-list"),
    path("diagnoses/<uuid:pk>/", AIDiagnosisDetailView.as_view(), name="ai-diagnosis-detail"),
    path("diagnose/", create_ai_diagnosis, name="ai-diagnose"),
]
