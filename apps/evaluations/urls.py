# apps/evaluations/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EvaluationViewSet, student_rating_view

app_name = "evaluations"

router = DefaultRouter()
router.register(r"", EvaluationViewSet, basename="evaluations")

urlpatterns = [
    path("", include(router.urls)),
    path("students/<uuid:student_id>/rating/", student_rating_view, name="student-evaluation-rating"),
    path("students/<uuid:student_id>/statistics/", student_rating_view, name="student-evaluation-statistics"),
]
