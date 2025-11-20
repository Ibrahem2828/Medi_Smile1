# accounts/urls.py
from django.urls import path
from .views import (
    # LoginView, LogoutView,
    PatientListView, PatientCreateView, PatientDetailView, PatientUpdateView, PatientDeleteView,
    StudentListView, StudentCreateView, StudentDetailView, StudentUpdateView, StudentDeleteView,
    SupervisorListView, SupervisorCreateView, SupervisorDetailView, SupervisorUpdateView, SupervisorDeleteView,
    UniversityAdminListView, UniversityAdminCreateView, UniversityAdminDetailView, UniversityAdminUpdateView, UniversityAdminDeleteView,
    TechSupportListView, TechSupportCreateView, TechSupportDetailView, TechSupportUpdateView, TechSupportDeleteView
)

urlpatterns = [
    # Authentication (disabled temporarily)
    # path('login/', LoginView.as_view(), name='login'),
    # path('logout/', LogoutView.as_view(), name='logout'),

    # Patients
    path('patients/', PatientListView.as_view(), name='patient-list'),
    path('patients/create/', PatientCreateView.as_view(), name='patient-create'),
    path('patients/<uuid:user_id>/', PatientDetailView.as_view(), name='patient-detail'),
    path('patients/<uuid:user_id>/update/', PatientUpdateView.as_view(), name='patient-update'),
    path('patients/<uuid:user_id>/delete/', PatientDeleteView.as_view(), name='patient-delete'),
    
    # Students
    path('students/', StudentListView.as_view(), name='student-list'),
    path('students/create/', StudentCreateView.as_view(), name='student-create'),
    path('students/<uuid:user_id>/', StudentDetailView.as_view(), name='student-detail'),
    path('students/<uuid:user_id>/update/', StudentUpdateView.as_view(), name='student-update'),
    path('students/<uuid:user_id>/delete/', StudentDeleteView.as_view(), name='student-delete'),
    
    # Supervisors
    path('supervisors/', SupervisorListView.as_view(), name='supervisor-list'),
    path('supervisors/create/', SupervisorCreateView.as_view(), name='supervisor-create'),
    path('supervisors/<uuid:user_id>/', SupervisorDetailView.as_view(), name='supervisor-detail'),
    path('supervisors/<uuid:user_id>/update/', SupervisorUpdateView.as_view(), name='supervisor-update'),
    path('supervisors/<uuid:user_id>/delete/', SupervisorDeleteView.as_view(), name='supervisor-delete'),
    
    # University Admins
    path('university-admins/', UniversityAdminListView.as_view(), name='university-admin-list'),
    path('university-admins/create/', UniversityAdminCreateView.as_view(), name='university-admin-create'),
    path('university-admins/<uuid:user_id>/', UniversityAdminDetailView.as_view(), name='university-admin-detail'),
    path('university-admins/<uuid:user_id>/update/', UniversityAdminUpdateView.as_view(), name='university-admin-update'),
    path('university-admins/<uuid:user_id>/delete/', UniversityAdminDeleteView.as_view(), name='university-admin-delete'),
    
    # Tech Support
    path('tech-support/', TechSupportListView.as_view(), name='tech-support-list'),
    path('tech-support/create/', TechSupportCreateView.as_view(), name='tech-support-create'),
    path('tech-support/<uuid:user_id>/', TechSupportDetailView.as_view(), name='tech-support-detail'),
    path('tech-support/<uuid:user_id>/update/', TechSupportUpdateView.as_view(), name='tech-support-update'),
    path('tech-support/<uuid:user_id>/delete/', TechSupportDeleteView.as_view(), name='tech-support-delete'),
]