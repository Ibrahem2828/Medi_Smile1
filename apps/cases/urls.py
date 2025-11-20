from django.urls import path
from . import views

urlpatterns = [
    path('', views.CaseListView.as_view(), name='case-list'),
    path('<uuid:pk>/', views.CaseDetailView.as_view(), name='case-detail'),
    path('<uuid:case_id>/assignment-requests/', views.CaseAssignmentRequestListView.as_view(), name='case-assignment-requests'),
    path('assignment-requests/<uuid:pk>/', views.CaseAssignmentRequestDetailView.as_view(), name='assignment-request-detail'),
    path('<uuid:case_id>/request-assign/', views.request_case_assignment, name='request-case-assignment'),
    path('<uuid:case_id>/supervisor-action/', views.supervisor_case_action, name='supervisor-case-action'),
]