from django.urls import path
from .views import (
    UniversityListView, UniversityDetailView, 
    UniversityCoursesView, CourseDetailView,
    UniversityCreateView, UniversityUpdateView, UniversityDeleteView,
    CourseCreateView, CourseUpdateView, CourseDeleteView
)

urlpatterns = [
    # Universities
    path('', UniversityListView.as_view(), name='university-list'),
    path('create/', UniversityCreateView.as_view(), name='university-create'),
    path('<uuid:pk>/', UniversityDetailView.as_view(), name='university-detail'),
    path('<uuid:pk>/update/', UniversityUpdateView.as_view(), name='university-update'),
    path('<uuid:pk>/delete/', UniversityDeleteView.as_view(), name='university-delete'),
    
    # Courses
    path('<uuid:university_id>/courses/', UniversityCoursesView.as_view(), name='university-courses'),
    path('<uuid:university_id>/courses/create/', CourseCreateView.as_view(), name='course-create'),
    path('courses/<uuid:pk>/', CourseDetailView.as_view(), name='course-detail'),
    path('courses/<uuid:pk>/update/', CourseUpdateView.as_view(), name='course-update'),
    path('courses/<uuid:pk>/delete/', CourseDeleteView.as_view(), name='course-delete'),
]