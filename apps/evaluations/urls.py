# apps/evaluations/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import EvaluationViewSet, student_evaluation_statistics

router = DefaultRouter()
router.register(r"", EvaluationViewSet, basename="evaluations")

urlpatterns = [
    # CRUD + actions (list, retrieve, create, update, submit, finalize)
    path("", include(router.urls)),

    # Student evaluation statistics
    path(
        "students/<uuid:student_id>/statistics/",
        student_evaluation_statistics,
        name="student-evaluation-statistics",
    ),
]
