# apps/community/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ContentViewSet, student_public_rating_view

app_name = "community"

router = DefaultRouter()
router.register(r"content", ContentViewSet, basename="content")

urlpatterns = [
    # Community content APIs
    path("", include(router.urls)),
    # Alias for pending approvals (moderators)
    path("approvals/", ContentViewSet.as_view({"get": "pending"}), name="content-approvals"),

    # Student public rating
    path(
        "students/<uuid:student_id>/rating/",
        student_public_rating_view,
        name="student-public-rating",
    ),
]
