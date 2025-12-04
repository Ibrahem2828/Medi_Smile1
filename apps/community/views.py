from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
from .models import Content, ContentLike, ContentComment
from .serializers import (
    ContentSerializer, ContentCreateSerializer, ContentUpdateSerializer,
    ContentCommentSerializer, ContentCommentCreateSerializer
)
from apps.accounts.permissions import IsStudent, IsSupervisor, IsUniversityAdmin


class ContentListView(generics.ListCreateAPIView):
    """API view for listing and creating content."""
    
    serializer_class = ContentSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_queryset(self):
        """Get content based on filters."""
        queryset = Content.objects.filter(is_public=True)
        
        # Filter by content type
        content_type = self.request.query_params.get('type')
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by university
        university_id = self.request.query_params.get('university')
        if university_id:
            queryset = queryset.filter(university_id=university_id)
        
        # Filter by featured
        featured = self.request.query_params.get('featured')
        if featured and featured.lower() == 'true':
            queryset = queryset.filter(is_featured=True)
        
        # Order by
        order_by = self.request.query_params.get('order_by', '-created_at')
        if order_by in ['created_at', '-created_at', 'view_count', '-view_count', 'title', '-title']:
            queryset = queryset.order_by(order_by)
        
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == 'POST':
            return ContentCreateSerializer
        return ContentSerializer
    
    def perform_create(self, serializer):
        """Create a new content."""
        serializer.save()


class ContentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API view for retrieving, updating and deleting content."""
    
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method in ['PUT', 'PATCH']:
            return ContentUpdateSerializer
        return ContentSerializer
    
    def get_permissions(self):
        """Get permissions based on request method."""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            # return [permissions.IsAuthenticated(), IsStudent() | IsSupervisor() | IsUniversityAdmin()]  # معلق مؤقتاً
            return [AllowAny()]  # مؤقتاً للسماح بالوصول بدون مصادقة
        # return [permissions.IsAuthenticated()]  # معلق مؤقتاً
        return [AllowAny()]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count when retrieving content."""
        instance = self.get_object()
        instance.view_count += 1
        instance.save(update_fields=['view_count'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ContentCommentListView(generics.ListCreateAPIView):
    """API view for listing and creating content comments."""
    
    serializer_class = ContentCommentSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_queryset(self):
        """Get comments for a specific content."""
        content_id = self.kwargs.get('content_id')
        return ContentComment.objects.filter(content_id=content_id, is_approved=True, parent=None)
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == 'POST':
            return ContentCommentCreateSerializer
        return ContentCommentSerializer
    
    def perform_create(self, serializer):
        """Create a new content comment."""
        content_id = self.kwargs.get('content_id')
        serializer.save(content_id=content_id)


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def like_content(request, content_id):
    """Like or unlike content."""
    try:
        content = Content.objects.get(id=content_id)
    except Content.DoesNotExist:
        return Response({
            'error': _('Content not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = request.user
    
    # Check if user already liked the content
    like, created = ContentLike.objects.get_or_create(
        content=content,
        user=user
    )
    
    if not created:
        # User already liked, so unlike
        like.delete()
        return Response({
            'message': _('Content unliked successfully'),
            'liked': False
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'message': _('Content liked successfully'),
            'liked': True
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def trending_content(request):
    """Get trending content based on views and likes."""
    # Get content with most views and likes in the last 7 days
    from django.utils import timezone
    from datetime import timedelta
    
    week_ago = timezone.now() - timedelta(days=7)
    
    content = Content.objects.filter(
        created_at__gte=week_ago,
        is_public=True
    ).annotate(
        likes_count=Count('likes')
    ).order_by('-view_count', '-likes_count')[:10]
    
    serializer = ContentSerializer(content, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)