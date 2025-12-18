from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from apps.accounts import models
from .models import AuditLog
from .serializers import AuditLogSerializer
from apps.accounts.permissions import IsUniversityAdmin, IsTechSupport
from rest_framework.permissions import IsAuthenticated


class AuditLogListView(generics.ListAPIView):
    """API view for listing audit logs."""
    
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsUniversityAdmin | IsTechSupport]
    
    def get_queryset(self):
        """Get audit logs based on filters."""
        queryset = AuditLog.objects.all()
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        # Filter by content type
        content_type = self.request.query_params.get('content_type')
        if content_type:
            from django.contrib.contenttypes.models import ContentType
            try:
                ct = ContentType.objects.get(model=content_type)
                queryset = queryset.filter(content_type=ct)
            except ContentType.DoesNotExist:
                pass
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Search in description
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(additional_data__icontains=search)
            )
        
        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsUniversityAdmin | IsTechSupport])
def audit_statistics(request):
    """Get audit statistics."""
    # Get count of logs by action
    action_counts = AuditLog.objects.values('action').annotate(count=models.Count('action'))
    
    # Get count of logs by user
    user_counts = AuditLog.objects.values('user__username').annotate(count=models.Count('user')).order_by('-count')[:10]
    
    # Get count of logs by day (last 30 days)
    from django.utils import timezone
    from datetime import timedelta
    import datetime
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_counts = []
    
    for i in range(30):
        day = thirty_days_ago + timedelta(days=i)
        next_day = day + timedelta(days=1)
        count = AuditLog.objects.filter(created_at__gte=day, created_at__lt=next_day).count()
        daily_counts.append({
            'date': day.strftime('%Y-%m-%d'),
            'count': count
        })
    
    return Response({
        'action_counts': list(action_counts),
        'top_users': list(user_counts),
        'daily_counts': daily_counts
    })