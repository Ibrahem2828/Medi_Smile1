from django.urls import path
from . import views

urlpatterns = [
    path('', views.EvaluationListView.as_view(), name='evaluation-list'),
    path('<uuid:pk>/', views.EvaluationDetailView.as_view(), name='evaluation-detail'),
    path('students/<uuid:student_id>/average-ratings/', views.student_average_ratings, name='student-average-ratings'),
]