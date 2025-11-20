from django.urls import path
from . import views

urlpatterns = [
    path('diagnoses/', views.AIDiagnosisListView.as_view(), name='ai-diagnosis-list'),
    path('diagnoses/<uuid:pk>/', views.AIDiagnosisDetailView.as_view(), name='ai-diagnosis-detail'),
    path('analyze/', views.analyze_symptoms, name='analyze-symptoms'),
]