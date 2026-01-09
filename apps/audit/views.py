# apps/audit/views.py
from datetime import datetime, time, timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import Role
from apps.accounts.permissions import IsUniversityAdmin, IsTechSupport
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """
    List audit logs with filtering.
    Roles:
    - University Admin: sees logs scoped to their university only
    - Tech Support: sees all logs
    """

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, (IsUniversityAdmin | IsTechSupport)]

    def get_queryset(self):
        qs = AuditLog.objects.select_related("user", "university", "content_type")

        user = self.request.user
        role_name = user.role.name

        # University scoping
        if role_name == Role.UNIVERSITY_ADMIN:
            qs = qs.filter(university_id=user.university_id)

        # Filters
        user_id = self.request.query_params.get("user_id")
        if user_id:
            qs = qs.filter(user_id=user_id)

        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        content_type_param = self.request.query_params.get("content_type")
        if content_type_param:
            try:
                ct = ContentType.objects.get(model=content_type_param)
                qs = qs.filter(content_type=ct)
            except ContentType.DoesNotExist:
                return AuditLog.objects.none()

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(description__icontains=search) |
                Q(metadata__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__username__icontains=search)
            )

        return qs.order_by("-created_at")


@api_view(["GET"])
@permission_classes([IsAuthenticated, (IsUniversityAdmin | IsTechSupport)])
def audit_statistics(request):
    """
    Aggregate audit statistics (last 30 days).
    Scoped by university for University Admin.
    """
    user = request.user
    role_name = getattr(getattr(user, "role", None), "name", None)
    qs = AuditLog.objects.all()

    if role_name == Role.UNIVERSITY_ADMIN:
        qs = qs.filter(university_id=user.university_id)

    today = timezone.localdate()
    start_day = today - timedelta(days=29)
    start_at = timezone.make_aware(datetime.combine(start_day, time.min))
    end_at = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min))
    qs = qs.filter(created_at__gte=start_at, created_at__lt=end_at)

    action_counts = list(
        qs.values("action")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    top_users = list(
        qs.exclude(user__isnull=True)
        .values("user__email")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    daily_counts_map = {
        row["day"]: row["count"]
        for row in (
            qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
        )
    }

    daily_counts = []
    for i in range(30):
        day = start_day + timedelta(days=i)
        daily_counts.append(
            {"date": day.strftime("%Y-%m-%d"), "count": daily_counts_map.get(day, 0)}
        )

    return Response(
        {
            "action_counts": action_counts,
            "top_users": top_users,
            "daily_activity": daily_counts,
        },
        status=status.HTTP_200_OK,
    )
