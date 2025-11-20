from django.urls import path
from . import views

urlpatterns = [
    path('logs/', views.AuditLogListView.as_view(), name='audit-log-list'),
    path('statistics/', views.audit_statistics, name='audit-statistics'),
]