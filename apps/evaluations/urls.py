# apps/evaluations/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import EvaluationViewSet, student_evaluation_statistics

app_name = "evaluations"

router = DefaultRouter()
router.register(r"", EvaluationViewSet, basename="evaluations")

urlpatterns = [
    path("", include(router.urls)),
    path("students/<uuid:student_id>/statistics/", student_evaluation_statistics, name="student-evaluation-statistics"),
]
