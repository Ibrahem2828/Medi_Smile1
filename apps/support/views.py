from rest_framework import generics, status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import SupportTicket, SupportTicketResponse
from .serializers import (
    SupportTicketCreateSerializer,
    SupportTicketListSerializer,
    SupportTicketDetailSerializer,
    SupportTicketUpdateSerializer,
    SupportTicketResponseCreateSerializer,
    SupportTicketResponseSerializer
)
from apps.accounts.permissions import IsTechSupport


class APIResponse:
    """Standardized API response format."""
    
    @staticmethod
    def success(message, data=None, status_code=status.HTTP_200_OK):
        return Response({
            "status": "success",
            "message": message,
            "data": data
        }, status=status_code)
    
    @staticmethod
    def error(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({
            "status": "error",
            "message": message,
            "errors": errors
        }, status=status_code)


# ==================== SUPPORT TICKET VIEWS ==================== #

class SupportTicketListView(generics.ListCreateAPIView):
    """API view to list and create support tickets."""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SupportTicketCreateSerializer
        return SupportTicketListSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = SupportTicket.objects.select_related('user', 'assigned_to').prefetch_related('responses').all()
        
        # If user is not tech support, only show their own tickets
        if user.role != 'tech_support':
            queryset = queryset.filter(user=user)
        
        # Filtering options
        status_filter = self.request.query_params.get('status', None)
        priority_filter = self.request.query_params.get('priority', None)
        category_filter = self.request.query_params.get('category', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success("تم جلب طلبات الدعم بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("فشل جلب طلبات الدعم.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            ticket = serializer.save()
            
            return APIResponse.success(
                "تم إنشاء طلب الدعم بنجاح.",
                SupportTicketDetailSerializer(ticket).data,
                status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return APIResponse.error("بيانات طلب الدعم غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل إنشاء طلب الدعم.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupportTicketDetailView(generics.RetrieveUpdateAPIView):
    """API view to retrieve and update support ticket details."""
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    lookup_url_kwarg = 'ticket_id'
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SupportTicketUpdateSerializer
        return SupportTicketDetailSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = SupportTicket.objects.select_related('user', 'assigned_to').prefetch_related('responses__user').all()
        
        # If user is not tech support, only allow access to their own tickets
        if user.role != 'tech_support':
            queryset = queryset.filter(user=user)
        
        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return APIResponse.success("تم جلب تفاصيل طلب الدعم بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("طلب الدعم غير موجود.", str(e), status.HTTP_404_NOT_FOUND)
    
    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            
            # Only tech support can update tickets
            if request.user.role != 'tech_support':
                return APIResponse.error(
                    "ليس لديك صلاحية لتعديل طلبات الدعم.",
                    None,
                    status.HTTP_403_FORBIDDEN
                )
            
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            ticket = serializer.save()
            
            return APIResponse.success(
                "تم تحديث طلب الدعم بنجاح.",
                SupportTicketDetailSerializer(ticket).data
            )
        except ValidationError as e:
            return APIResponse.error("بيانات التحديث غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل تحديث طلب الدعم.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupportTicketResponseListView(generics.ListCreateAPIView):
    """API view to list and create responses for a support ticket."""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SupportTicketResponseCreateSerializer
        return SupportTicketResponseSerializer
    
    def get_queryset(self):
        ticket_id = self.kwargs.get('ticket_id')
        ticket = get_object_or_404(SupportTicket, id=ticket_id)
        
        user = self.request.user
        queryset = SupportTicketResponse.objects.select_related('user').filter(ticket=ticket)
        
        # If user is not tech support, hide internal notes
        if user.role != 'tech_support':
            queryset = queryset.filter(is_internal=False)
        
        # If user is not tech support and not the ticket owner, deny access
        if user.role != 'tech_support' and ticket.user != user:
            return SupportTicketResponse.objects.none()
        
        return queryset
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        ticket_id = self.kwargs.get('ticket_id')
        ticket = get_object_or_404(SupportTicket, id=ticket_id)
        context['ticket'] = ticket
        return context
    
    def list(self, request, *args, **kwargs):
        try:
            ticket_id = self.kwargs.get('ticket_id')
            ticket = get_object_or_404(SupportTicket, id=ticket_id)
            
            # Check access
            if request.user.role != 'tech_support' and ticket.user != request.user:
                return APIResponse.error(
                    "ليس لديك صلاحية لعرض ردود هذا الطلب.",
                    None,
                    status.HTTP_403_FORBIDDEN
                )
            
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return APIResponse.success("تم جلب ردود الطلب بنجاح.", serializer.data)
        except Exception as e:
            return APIResponse.error("فشل جلب ردود الطلب.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create(self, request, *args, **kwargs):
        try:
            ticket_id = self.kwargs.get('ticket_id')
            ticket = get_object_or_404(SupportTicket, id=ticket_id)
            
            # Check access
            if request.user.role != 'tech_support' and ticket.user != request.user:
                return APIResponse.error(
                    "ليس لديك صلاحية للرد على هذا الطلب.",
                    None,
                    status.HTTP_403_FORBIDDEN
                )
            
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            response = serializer.save()
            
            return APIResponse.success(
                "تم إرسال الرد بنجاح.",
                SupportTicketResponseSerializer(response).data,
                status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return APIResponse.error("بيانات الرد غير صالحة.", e.detail, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error("فشل إرسال الرد.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupportTicketStatsView(APIView):
    """API view to get support ticket statistics (tech support only)."""
    permission_classes = [IsAuthenticated, IsTechSupport]
    
    def get(self, request, *args, **kwargs):
        try:
            stats = {
                'total': SupportTicket.objects.count(),
                'open': SupportTicket.objects.filter(status='open').count(),
                'in_progress': SupportTicket.objects.filter(status='in_progress').count(),
                'resolved': SupportTicket.objects.filter(status='resolved').count(),
                'closed': SupportTicket.objects.filter(status='closed').count(),
                'urgent': SupportTicket.objects.filter(priority='urgent', status__in=['open', 'in_progress']).count(),
                'medium': SupportTicket.objects.filter(priority='medium', status__in=['open', 'in_progress']).count(),
                'low': SupportTicket.objects.filter(priority='low', status__in=['open', 'in_progress']).count(),
            }
            
            return APIResponse.success("تم جلب إحصائيات طلبات الدعم بنجاح.", stats)
        except Exception as e:
            return APIResponse.error("فشل جلب الإحصائيات.", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)

