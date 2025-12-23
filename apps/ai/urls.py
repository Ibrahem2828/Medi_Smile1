# apps/ai/urls.py

from django.urls import path
from .views import (
    AIDiagnosisListView,
    AIDiagnosisDetailView,
    analyze_symptoms,
)

urlpatterns = [
    # =====================================================
    # AI Diagnoses
    # =====================================================
    path(
        "diagnoses/",
        AIDiagnosisListView.as_view(),
        name="ai-diagnosis-list",
    ),
    path(
        "diagnoses/<uuid:pk>/",
        AIDiagnosisDetailView.as_view(),
        name="ai-diagnosis-detail",
    ),

    # =====================================================
    # AI Analysis
    # =====================================================
    path(
        "analyze/",
        analyze_symptoms,
        name="ai-analyze-symptoms",
    ),
]
