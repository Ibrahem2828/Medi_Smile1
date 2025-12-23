# apps/audit/views.py

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.contenttypes.models import ContentType

from .models import AuditLog
from .serializers import AuditLogSerializer
from apps.accounts.permissions import IsUniversityAdmin, IsTechSupport


class AuditLogListView(generics.ListAPIView):
    """
    List audit logs with filtering.
    Accessible only by University Admin and Tech Support.
    """

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin | IsTechSupport]

    def get_queryset(self):
        queryset = AuditLog.objects.select_related(
            "user",
            "university",
            "content_type",
        )

        user = self.request.user

        # -------------------------
        # University scoping
        # -------------------------
        if user.role.name == "university_admin":
            queryset = queryset.filter(university__in=[
                getattr(user, "student_profile", None) and user.student_profile.university,
                getattr(user, "supervisor_profile", None) and user.supervisor_profile.university,
                getattr(user, "universityadmin_profile", None) and user.universityadmin_profile.university,
            ])

        # -------------------------
        # Filters
        # -------------------------
        user_id = self.request.query_params.get("user_id")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        action = self.request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)

        content_type_param = self.request.query_params.get("content_type")
        if content_type_param:
            try:
                ct = ContentType.objects.get(model=content_type_param)
                queryset = queryset.filter(content_type=ct)
            except ContentType.DoesNotExist:
                queryset = queryset.none()

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)

        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(metadata__icontains=search)
            )

        return queryset.order_by("-created_at")


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsUniversityAdmin | IsTechSupport])
def audit_statistics(request):
    """
    Aggregate audit statistics.
    """

    user = request.user
    queryset = AuditLog.objects.all()

    # University scoping
    if user.role.name == "university_admin":
        queryset = queryset.filter(university=getattr(user.universityadmin_profile, "university", None))

    # -------------------------
    # Aggregations
    # -------------------------
    action_counts = list(
        queryset.values("action")
        .annotate(count=Count("action"))
        .order_by("-count")
    )

    top_users = list(
        queryset.values("user__email")
        .annotate(count=Count("user"))
        .order_by("-count")[:10]
    )

    # Daily counts (last 30 days)
    today = timezone.now().date()
    daily_counts = []

    for i in range(30):
        day = today - timedelta(days=i)
        count = queryset.filter(created_at__date=day).count()
        daily_counts.append({
            "date": day.strftime("%Y-%m-%d"),
            "count": count,
        })

    daily_counts.reverse()

    return Response(
        {
            "action_counts": action_counts,
            "top_users": top_users,
            "daily_activity": daily_counts,
        },
        status=status.HTTP_200_OK,
    )
