from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from .models import Backup
from .serializers import (
    BackupSerializer,
    BackupCreateSerializer,
    BackupRestoreSerializer
)
from .services import BackupService
from .tasks import create_backup_task
import logging

logger = logging.getLogger(__name__)


class BackupViewSet(viewsets.ModelViewSet):
    """ViewSet لإدارة النسخ الاحتياطية"""
    
    queryset = Backup.objects.all()
    serializer_class = BackupSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        """تصفية النسخ الاحتياطية حسب النوع والحالة"""
        queryset = super().get_queryset()
        
        backup_type = self.request.query_params.get('type', None)
        status_filter = self.request.query_params.get('status', None)
        
        if backup_type:
            queryset = queryset.filter(backup_type=backup_type)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def create_backup(self, request):
        """إنشاء نسخة احتياطية جديدة"""
        serializer = BackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        backup_type = serializer.validated_data.get('backup_type', 'full')
        description = serializer.validated_data.get('description', None)
        
        # تشغيل المهمة بشكل غير متزامن
        task = create_backup_task.delay(backup_type, description)
        
        return Response({
            'message': 'تم بدء عملية النسخ الاحتياطي',
            'task_id': task.id,
            'backup_type': backup_type
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=False, methods=['post'])
    def create_backup_sync(self, request):
        """إنشاء نسخة احتياطية بشكل متزامن (للاستخدام الفوري)"""
        serializer = BackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        backup_type = serializer.validated_data.get('backup_type', 'full')
        description = serializer.validated_data.get('description', None)
        
        try:
            service = BackupService()
            
            if backup_type == 'database':
                backup = Backup.objects.create(
                    backup_type='database',
                    status='in_progress',
                    description=description
                )
                result = service.backup_database(backup)
                if result['success']:
                    backup.status = 'completed'
                    backup.save()
                else:
                    backup.status = 'failed'
                    backup.save()
            
            elif backup_type == 'files':
                backup = Backup.objects.create(
                    backup_type='files',
                    status='in_progress',
                    description=description
                )
                result = service.backup_files(backup)
                if result['success']:
                    backup.status = 'completed'
                    backup.save()
                else:
                    backup.status = 'failed'
                    backup.save()
            
            else:  # full
                backup = service.create_full_backup(description=description)
            
            response_serializer = BackupSerializer(backup)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Backup creation error: {str(e)}")
            return Response({
                'error': f'فشل إنشاء النسخة الاحتياطية: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """استعادة نسخة احتياطية"""
        backup = get_object_or_404(Backup, pk=pk)
        serializer = BackupRestoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        restore_type = serializer.validated_data.get('restore_type', 'full')
        
        if backup.status != 'completed':
            return Response({
                'error': 'لا يمكن استعادة نسخة احتياطية غير مكتملة'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = BackupService()
            
            if restore_type == 'database' or restore_type == 'full':
                if not backup.database_backup_path:
                    return Response({
                        'error': 'لا توجد نسخة احتياطية لقاعدة البيانات'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                result = service.restore_database(backup.database_backup_path)
                if not result['success']:
                    return Response({
                        'error': result.get('error', 'فشل استعادة قاعدة البيانات')
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if restore_type == 'files' or restore_type == 'full':
                if not backup.files_backup_path:
                    return Response({
                        'error': 'لا توجد نسخة احتياطية للملفات'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                result = service.restore_files(backup.files_backup_path)
                if not result['success']:
                    return Response({
                        'error': result.get('error', 'فشل استعادة الملفات')
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'message': 'تم استعادة النسخة الاحتياطية بنجاح',
                'restore_type': restore_type
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Restore error: {str(e)}")
            return Response({
                'error': f'فشل الاستعادة: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """إحصائيات النسخ الاحتياطية"""
        total_backups = Backup.objects.count()
        completed_backups = Backup.objects.filter(status='completed').count()
        failed_backups = Backup.objects.filter(status='failed').count()
        in_progress_backups = Backup.objects.filter(status='in_progress').count()
        
        total_size = sum(backup.total_size for backup in Backup.objects.filter(status='completed'))
        
        latest_backup = Backup.objects.filter(status='completed').first()
        
        return Response({
            'total_backups': total_backups,
            'completed_backups': completed_backups,
            'failed_backups': failed_backups,
            'in_progress_backups': in_progress_backups,
            'total_size': total_size,
            'total_size_display': self._format_size(total_size),
            'latest_backup': BackupSerializer(latest_backup).data if latest_backup else None
        })
    
    @action(detail=False, methods=['post'])
    def cleanup(self, request):
        """تنظيف النسخ الاحتياطية القديمة"""
        days_to_keep = request.data.get('days_to_keep', 30)
        
        try:
            service = BackupService()
            result = service.cleanup_old_backups(days_to_keep=days_to_keep)
            
            if result['success']:
                return Response({
                    'message': f'تم حذف {result["deleted_count"]} نسخة احتياطية قديمة'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': result.get('error', 'فشل تنظيف النسخ الاحتياطية')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
            return Response({
                'error': f'فشل التنظيف: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _format_size(self, size_bytes):
        """تحويل الحجم من bytes إلى شكل مقروء"""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"














