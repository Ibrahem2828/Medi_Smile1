from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.ReportListView.as_view(), name='report-list'),
    path('<uuid:pk>/', views.ReportDetailView.as_view(), name='report-detail'),
    path('student/<uuid:student_id>/', views.student_reports, name='student-reports'),
    path('university/<uuid:university_id>/', views.university_reports, name='university-reports'),
]


