# apps/audit/urls.py
from django.urls import path
from .views import AuditLogListView, audit_statistics

app_name = "audit"

urlpatterns = [
    path("logs/", AuditLogListView.as_view(), name="audit-log-list"),
    path("statistics/", audit_statistics, name="audit-statistics"),
]
