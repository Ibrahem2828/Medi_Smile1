from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
from .models import Appointment
from .serializers import AppointmentSerializer, AppointmentCreateSerializer, AppointmentUpdateSerializer
from apps.accounts.permissions import IsPatient, IsStudent, IsSupervisor
from apps.notifications.utils import notify_appointment_status_change


class AppointmentListView(generics.ListCreateAPIView):
    """API view for listing and creating appointments."""
    
    serializer_class = AppointmentSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_queryset(self):
        """Get appointments based on user role."""
        user = self.request.user
        status_filter = self.request.query_params.get('status')
        
        if user.role == 'patient':
            appointments = Appointment.objects.filter(patient=user)
        elif user.role == 'supervisor':
            # Supervisor sees appointments related to cases they supervise
            from apps.cases.models import Case
            supervised_case_ids = Case.objects.filter(supervisor=user).values_list('id', flat=True)
            appointments = Appointment.objects.filter(case_id__in=supervised_case_ids)
        elif user.role in ['university_admin', 'tech_support']:
            appointments = Appointment.objects.all()
        else:
            # For any user (student, doctor, staff, etc.)
            appointments = Appointment.objects.filter(user=user)
        
        # Filter by status if provided
        if status_filter:
            appointments = appointments.filter(status=status_filter)
        
        # Filter out archived appointments by default
        appointments = appointments.filter(is_archived=False)
        
        return appointments
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == 'POST':
            return AppointmentCreateSerializer
        return AppointmentSerializer
    
    def perform_create(self, serializer):
        """Create a new appointment."""
        serializer.save()


class AppointmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API view for retrieving, updating and deleting an appointment."""
    
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    # permission_classes = [permissions.IsAuthenticated]  # معلق مؤقتاً - تم تعطيل المصادقة
    permission_classes = [AllowAny]  # مؤقتاً للسماح بالوصول بدون مصادقة
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method in ['PUT', 'PATCH']:
            return AppointmentUpdateSerializer
        return AppointmentSerializer
    
    def get_permissions(self):
        """Get permissions based on request method."""
        if self.request.method in ['PUT', 'PATCH']:
            # return [permissions.IsAuthenticated()]  # معلق مؤقتاً
            return [AllowAny()]  # مؤقتاً للسماح بالوصول بدون مصادقة
        elif self.request.method == 'DELETE':
            # return [permissions.IsAuthenticated(), IsPatient()]  # معلق مؤقتاً
            return [AllowAny()]  # مؤقتاً للسماح بالوصول بدون مصادقة
        # return [permissions.IsAuthenticated()]  # معلق مؤقتاً
        return [AllowAny()]  # مؤقتاً للسماح بالوصول بدون مصادقة


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def confirm_appointment(request, appointment_id):
    """Confirm an appointment."""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return Response({
            'error': _('Appointment not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = request.user
    
    # Check if user is authorized to confirm
    if user.role == 'patient' and appointment.patient != user:
        return Response({
            'error': _('You are not authorized to confirm this appointment')
        }, status=status.HTTP_403_FORBIDDEN)
    
    if appointment.user != user:
        return Response({
            'error': _('You are not authorized to confirm this appointment')
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check if appointment is in scheduled status
    if appointment.status != 'scheduled':
        return Response({
            'error': _('Appointment cannot be confirmed')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Store old status
    old_status = appointment.status
    
    # Update appointment status
    appointment.status = 'confirmed'
    appointment.save()
    
    # Send automatic notification
    try:
        notify_appointment_status_change(appointment, old_status, 'confirmed', user)
    except Exception as e:
        print(f"Error sending notification: {e}")
    
    return Response({
        'message': _('Appointment confirmed successfully'),
        'appointment': AppointmentSerializer(appointment).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def complete_appointment(request, appointment_id):
    """Complete an appointment."""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return Response({
            'error': _('Appointment not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = request.user
    
    # Check if user is authorized to complete
    if appointment.user != user:
        return Response({
            'error': _('You are not authorized to complete this appointment')
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check if appointment is in confirmed or in_progress status
    if appointment.status not in ['confirmed', 'in_progress']:
        return Response({
            'error': _('Appointment cannot be completed')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Store old status
    old_status = appointment.status
    
    # Update appointment status
    appointment.status = 'completed'
    appointment.save()
    
    # Send automatic notification
    try:
        notify_appointment_status_change(appointment, old_status, 'completed', user)
    except Exception as e:
        print(f"Error sending notification: {e}")
    
    return Response({
        'message': _('Appointment completed successfully'),
        'appointment': AppointmentSerializer(appointment).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def cancel_appointment(request, appointment_id):
    """Cancel an appointment."""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return Response({
            'error': _('Appointment not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = request.user
    
    # Check if user is authorized to cancel
    if user.role == 'patient' and appointment.patient != user:
        return Response({
            'error': _('You are not authorized to cancel this appointment')
        }, status=status.HTTP_403_FORBIDDEN)
    
    if appointment.user != user:
        return Response({
            'error': _('You are not authorized to cancel this appointment')
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check if appointment is in scheduled or confirmed status
    if appointment.status not in ['scheduled', 'confirmed']:
        return Response({
            'error': _('Appointment cannot be cancelled')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Store old status
    old_status = appointment.status
    
    # Update appointment status
    appointment.status = 'cancelled'
    appointment.save()
    
    # Send automatic notification
    try:
        notify_appointment_status_change(appointment, old_status, 'cancelled', user)
    except Exception as e:
        print(f"Error sending notification: {e}")
    
    return Response({
        'message': _('Appointment cancelled successfully'),
        'appointment': AppointmentSerializer(appointment).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def start_appointment(request, appointment_id):
    """Start an appointment (change status to in_progress)."""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return Response({
            'error': _('Appointment not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = request.user
    
    # Check if user is authorized to start
    if appointment.user != user:
        return Response({
            'error': _('You are not authorized to start this appointment')
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check if appointment is in confirmed status
    if appointment.status != 'confirmed':
        return Response({
            'error': _('Appointment must be confirmed before starting')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Store old status
    old_status = appointment.status
    
    # Update appointment status
    appointment.status = 'in_progress'
    appointment.save()
    
    # Note: in_progress doesn't have a notification type, but we can create a custom one if needed
    # For now, we'll skip notification for in_progress
    
    return Response({
        'message': _('Appointment started successfully'),
        'appointment': AppointmentSerializer(appointment).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
# @permission_classes([permissions.IsAuthenticated])  # معلق مؤقتاً - تم تعطيل المصادقة
@permission_classes([AllowAny])  # مؤقتاً للسماح بالوصول بدون مصادقة
def mark_no_show(request, appointment_id):
    """Mark an appointment as no show."""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return Response({
            'error': _('Appointment not found')
        }, status=status.HTTP_404_NOT_FOUND)
    
    user = request.user
    
    # Check if user is authorized
    if appointment.user != user:
        return Response({
            'error': _('You are not authorized to mark this appointment as no show')
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Check if appointment is in confirmed or in_progress status
    if appointment.status not in ['confirmed', 'in_progress']:
        return Response({
            'error': _('Appointment cannot be marked as no show')
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Update appointment status
    appointment.status = 'no_show'
    appointment.save()
    
    return Response({
        'message': _('Appointment marked as no show successfully'),
        'appointment': AppointmentSerializer(appointment).data
    }, status=status.HTTP_200_OK)