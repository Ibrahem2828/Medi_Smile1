from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse, Http404
from .models import Attachment
from .serializers import AttachmentSerializer, AttachmentCreateSerializer
from apps.accounts.permissions import IsPatient, IsStudent, IsSupervisor


class AttachmentListView(generics.ListCreateAPIView):
    """API view for listing and creating attachments."""
    
    serializer_class = AttachmentSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_queryset(self):
        """Get attachments based on user role and filters."""
        user = self.request.user
        
        # Filter by reference
        case_id = self.request.query_params.get('case_id')
        appointment_id = self.request.query_params.get('appointment_id')
        message_id = self.request.query_params.get('message_id')
        content_id = self.request.query_params.get('content_id')
        
        if user.role == 'patient':
            # Patients can see their own attachments and public ones
            attachments = Attachment.objects.filter(uploaded_by=user) | Attachment.objects.filter(is_public=True)
        elif user.role == 'student':
            # Students can see their own attachments, public ones, and those related to their cases
            from apps.cases.models import Case
            case_ids = Case.objects.filter(student=user).values_list('id', flat=True)
            attachments = Attachment.objects.filter(
                uploaded_by=user
            ) | Attachment.objects.filter(
                is_public=True
            ) | Attachment.objects.filter(
                case_id__in=case_ids
            )
        elif user.role == 'supervisor':
            # Supervisors can see their own attachments, public ones, and those related to their cases
            from apps.cases.models import Case
            case_ids = Case.objects.filter(supervisor=user).values_list('id', flat=True)
            attachments = Attachment.objects.filter(
                uploaded_by=user
            ) | Attachment.objects.filter(
                is_public=True
            ) | Attachment.objects.filter(
                case_id__in=case_ids
            )
        elif user.role in ['university_admin', 'tech_support']:
            # Admins can see all attachments
            attachments = Attachment.objects.all()
        else:
            attachments = Attachment.objects.none()
        
        # Filter by reference if provided
        if case_id:
            attachments = attachments.filter(case_id=case_id)
        if appointment_id:
            attachments = attachments.filter(appointment_id=appointment_id)
        if message_id:
            attachments = attachments.filter(message_id=message_id)
        if content_id:
            attachments = attachments.filter(content_id=content_id)
        
        return attachments.distinct()
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == 'POST':
            return AttachmentCreateSerializer
        return AttachmentSerializer
    
    def perform_create(self, serializer):
        """Create a new attachment."""
        serializer.save()


class AttachmentDetailView(generics.RetrieveDestroyAPIView):
    """API view for retrieving and deleting an attachment."""
    
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_permissions(self):
        """Get permissions based on request method."""
        if self.request.method == 'DELETE':
            # return [permissions.IsAuthenticated(), IsPatient() | IsStudent() | IsSupervisor()]  # معلق مؤقتاً
            return [AllowAny()]  # مؤقتاً للسماح بالوصول بدون مصادقة
        # return [permissions.IsAuthenticated()]  # معلق مؤقتاً
        return [AllowAny()]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_object(self):
        """Get attachment if user has permission."""
        obj = super().get_object()
        user = self.request.user
        
        # Check if user has permission to access this attachment
        if user.role == 'patient' and obj.uploaded_by != user and not obj.is_public:
            raise Http404(_("Attachment not found"))
        elif user.role == 'student':
            from apps.cases.models import Case
            if obj.uploaded_by != user and not obj.is_public:
                # Check if attachment is related to student's case
                if obj.case_id and not Case.objects.filter(id=obj.case_id, student=user).exists():
                    raise Http404(_("Attachment not found"))
        elif user.role == 'supervisor':
            from apps.cases.models import Case
            if obj.uploaded_by != user and not obj.is_public:
                # Check if attachment is related to supervisor's case
                if obj.case_id and not Case.objects.filter(id=obj.case_id, supervisor=user).exists():
                    raise Http404(_("Attachment not found"))
        
        return obj


@api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def download_attachment(request, attachment_id):
    """Download an attachment."""
    try:
        attachment = Attachment.objects.get(id=attachment_id)
    except Attachment.DoesNotExist:
        return Response({
            'error': _('Attachment not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = request.user
    
    # Check if user has permission to download this attachment
    if user.role == 'patient' and attachment.uploaded_by != user and not attachment.is_public:
        return Response({
            'error': _('You do not have permission to download this attachment')
        }, status=status.HTTP_403_FORBIDDEN)
    elif user.role == 'student':
        from apps.cases.models import Case
        if attachment.uploaded_by != user and not attachment.is_public:
            # Check if attachment is related to student's case
            if attachment.case_id and not Case.objects.filter(id=attachment.case_id, student=user).exists():
                return Response({
                    'error': _('You do not have permission to download this attachment')
                }, status=status.HTTP_403_FORBIDDEN)
    elif user.role == 'supervisor':
        from apps.cases.models import Case
        if attachment.uploaded_by != user and not attachment.is_public:
            # Check if attachment is related to supervisor's case
            if attachment.case_id and not Case.objects.filter(id=attachment.case_id, supervisor=user).exists():
                return Response({
                    'error': _('You do not have permission to download this attachment')
                }, status=status.HTTP_403_FORBIDDEN)
    
    # Return file for download
    if attachment.file:
        response = HttpResponse(attachment.file, content_type=attachment.mime_type)
        response['Content-Disposition'] = f'attachment; filename="{attachment.original_filename}"'
        return response
    
    return Response({
        'error': _('File not found')
    }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def preview_attachment(request, attachment_id):
    """Preview an attachment (for images only)."""
    try:
        attachment = Attachment.objects.get(id=attachment_id)
    except Attachment.DoesNotExist:
        return Response({
            'error': _('Attachment not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Check if attachment is an image
    if not attachment.is_image():
        return Response({
            'error': _('Attachment is not an image')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    
    # Check if user has permission to preview this attachment
    if user.role == 'patient' and attachment.uploaded_by != user and not attachment.is_public:
        return Response({
            'error': _('You do not have permission to preview this attachment')
        }, status=status.HTTP_403_FORBIDDEN)
    elif user.role == 'student':
        from apps.cases.models import Case
        if attachment.uploaded_by != user and not attachment.is_public:
            # Check if attachment is related to student's case
            if attachment.case_id and not Case.objects.filter(id=attachment.case_id, student=user).exists():
                return Response({
                    'error': _('You do not have permission to preview this attachment')
                }, status=status.HTTP_403_FORBIDDEN)
    elif user.role == 'supervisor':
        from apps.cases.models import Case
        if attachment.uploaded_by != user and not attachment.is_public:
            # Check if attachment is related to supervisor's case
            if attachment.case_id and not Case.objects.filter(id=attachment.case_id, supervisor=user).exists():
                return Response({
                    'error': _('You do not have permission to preview this attachment')
                }, status=status.HTTP_403_FORBIDDEN)
    
    # Return image for preview
    if attachment.file:
        response = HttpResponse(attachment.file, content_type=attachment.mime_type)
        return response
    
    return Response({
        'error': _('File not found')
    }, status=status.HTTP_404_NOT_FOUND)