from django.urls import path

from .views import (
    AIDiagnosisListView,
    AIDiagnosisDetailView,
    create_ai_diagnosis,
)

urlpatterns = [
    # =====================================================
    # AI Diagnosis Endpoints
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
    # AI Diagnosis Creation (Patient Only)
    # =====================================================

    path(
        "diagnose/",
        create_ai_diagnosis,
        name="ai-diagnose",
    ),
]
