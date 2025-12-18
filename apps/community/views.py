from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q
from django.utils import timezone
from .models import Content, ContentLike, ContentComment
from .serializers import (
    ContentSerializer, ContentCreateSerializer, ContentUpdateSerializer,
    ContentCommentSerializer, ContentCommentCreateSerializer
)
from apps.accounts.permissions import IsStudent, IsSupervisor, IsUniversityAdmin
from apps.accounts.models import User
from medismile.utils.auth import resolve_request_user, require_request_user


class ContentListView(generics.ListCreateAPIView):
    """API view for listing and creating content."""
    
    serializer_class = ContentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get content based on filters."""
        user = resolve_request_user(self.request)
        
        # Base queryset: approved and public content
        queryset = Content.objects.filter(is_public=True, status='approved')
        
        # If user is a student, also show their own pending/rejected content
        if user and user.role == 'student':
            queryset = Content.objects.filter(
                Q(is_public=True, status='approved') | Q(author=user)
            )
        
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
        
        # Filter by status (for students to see their own content status)
        status_filter = self.request.query_params.get('status')
        if status_filter and user and user.role == 'student':
            queryset = queryset.filter(author=user, status=status_filter)
        
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
        """Create a new content and send notification to supervisor if student."""
        content = serializer.save()
        
        # If student created content, send notification to supervisors
        if content.author.role == 'student' and content.status == 'pending':
            from apps.notifications.utils import create_content_approval_notification
            create_content_approval_notification(content)


class ContentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API view for retrieving, updating and deleting content."""
    
    queryset = Content.objects.all()
    serializer_class = ContentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method in ['PUT', 'PATCH']:
            return ContentUpdateSerializer
        return ContentSerializer
    
    def get_permissions(self):
        """Get permissions based on request method."""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsStudent() | IsSupervisor() | IsUniversityAdmin()]
        return [IsAuthenticated()]
    
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
    permission_classes = [IsAuthenticated]
    
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
@permission_classes([IsAuthenticated])
def like_content(request, content_id):
    """Like or unlike content."""
    try:
        content = Content.objects.get(id=content_id)
    except Content.DoesNotExist:
        return Response({
            'error': _('Content not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    user, error = require_request_user(request, error_key='user_id')
    if error:
        return error
    
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
@permission_classes([IsAuthenticated])
def trending_content(request):
    """Get trending content based on views and likes."""
    # Get content with most views and likes in the last 7 days
    from django.utils import timezone
    from datetime import timedelta
    
    week_ago = timezone.now() - timedelta(days=7)
    
    content = Content.objects.filter(
        created_at__gte=week_ago,
        is_public=True,
        status='approved'  # Only approved content
    ).annotate(
        likes_count=Count('likes')
    ).order_by('-view_count', '-likes_count')[:10]
    
    serializer = ContentSerializer(content, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSupervisor | IsUniversityAdmin])
def pending_content(request):
    """Get pending content for supervisor approval."""
    user, error = require_request_user(request, error_key='user_id')
    if error:
        return error
    
    # Only supervisors and admins can see pending content
    if user.role not in ['supervisor', 'university_admin', 'tech_support']:
        return Response({
            'error': _('You are not authorized to view pending content')
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Get pending content from same university
    queryset = Content.objects.filter(status='pending')
    
    # If supervisor, only show content from their university
    if user.role == 'supervisor':
        if hasattr(user, 'supervisorprofile') and user.supervisorprofile.university:
            queryset = queryset.filter(university=user.supervisorprofile.university)
    
    serializer = ContentSerializer(queryset, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSupervisor | IsUniversityAdmin])
def approve_content(request, content_id):
    """Approve a pending content."""
    user, error = require_request_user(request, error_key='user_id')
    if error:
        return error
    
    # Only supervisors and admins can approve
    if user.role not in ['supervisor', 'university_admin', 'tech_support']:
        return Response({
            'error': _('You are not authorized to approve content')
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        content = Content.objects.get(id=content_id, status='pending')
    except Content.DoesNotExist:
        return Response({
            'error': _('Content not found or already processed')
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if supervisor is from same university
    if user.role == 'supervisor':
        if hasattr(user, 'supervisorprofile') and user.supervisorprofile.university:
            if content.university != user.supervisorprofile.university:
                return Response({
                    'error': _('You can only approve content from your university')
                }, status=status.HTTP_403_FORBIDDEN)
    
    # Approve content
    content.status = 'approved'
    content.approved_by = user
    content.approved_at = timezone.now()
    content.save()
    
    # Send notification to student
    from apps.notifications.utils import create_content_approved_notification
    create_content_approved_notification(content, user)
    
    serializer = ContentSerializer(content, context={'request': request})
    return Response({
        'message': _('Content approved successfully'),
        'content': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSupervisor | IsUniversityAdmin])
def reject_content(request, content_id):
    """Reject a pending content."""
    user, error = require_request_user(request, error_key='user_id')
    if error:
        return error
    
    # Only supervisors and admins can reject
    if user.role not in ['supervisor', 'university_admin', 'tech_support']:
        return Response({
            'error': _('You are not authorized to reject content')
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        content = Content.objects.get(id=content_id, status='pending')
    except Content.DoesNotExist:
        return Response({
            'error': _('Content not found or already processed')
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if supervisor is from same university
    if user.role == 'supervisor':
        if hasattr(user, 'supervisorprofile') and user.supervisorprofile.university:
            if content.university != user.supervisorprofile.university:
                return Response({
                    'error': _('You can only reject content from your university')
                }, status=status.HTTP_403_FORBIDDEN)
    
    # Get rejection reason
    rejection_reason = request.data.get('rejection_reason', '')
    
    # Reject content
    content.status = 'rejected'
    content.approved_by = user
    content.approved_at = timezone.now()
    content.rejection_reason = rejection_reason
    content.save()
    
    # Send notification to student
    from apps.notifications.utils import create_content_rejected_notification
    create_content_rejected_notification(content, user, rejection_reason)
    
    serializer = ContentSerializer(content, context={'request': request})
    return Response({
        'message': _('Content rejected successfully'),
        'content': serializer.data
    }, status=status.HTTP_200_OK)