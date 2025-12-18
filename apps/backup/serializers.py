from rest_framework import serializers
from .models import Backup


class BackupSerializer(serializers.ModelSerializer):
    """Serializer للنسخ الاحتياطي"""
    
    duration_display = serializers.SerializerMethodField()
    database_size_display = serializers.SerializerMethodField()
    files_size_display = serializers.SerializerMethodField()
    total_size_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Backup
        fields = [
            'id',
            'backup_type',
            'status',
            'database_backup_path',
            'files_backup_path',
            'database_size',
            'files_size',
            'total_size',
            'description',
            'error_message',
            'storage_type',
            'storage_path',
            'created_at',
            'started_at',
            'completed_at',
            'duration',
            'duration_display',
            'database_size_display',
            'files_size_display',
            'total_size_display',
        ]
        read_only_fields = [
            'id',
            'status',
            'database_backup_path',
            'files_backup_path',
            'database_size',
            'files_size',
            'total_size',
            'error_message',
            'created_at',
            'started_at',
            'completed_at',
            'duration',
        ]
    
    def get_duration_display(self, obj):
        """عرض مدة النسخ الاحتياطي بشكل مقروء"""
        duration = obj.duration
        if duration:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            if hours > 0:
                return f"{hours}س {minutes}د {seconds}ث"
            elif minutes > 0:
                return f"{minutes}د {seconds}ث"
            else:
                return f"{seconds}ث"
        return None
    
    def get_database_size_display(self, obj):
        """عرض حجم قاعدة البيانات بشكل مقروء"""
        return self._format_size(obj.database_size)
    
    def get_files_size_display(self, obj):
        """عرض حجم الملفات بشكل مقروء"""
        return self._format_size(obj.files_size)
    
    def get_total_size_display(self, obj):
        """عرض الحجم الإجمالي بشكل مقروء"""
        return self._format_size(obj.total_size)
    
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


class BackupCreateSerializer(serializers.Serializer):
    """Serializer لإنشاء نسخة احتياطية"""
    
    backup_type = serializers.ChoiceField(
        choices=['database', 'files', 'full'],
        default='full'
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True
    )


class BackupRestoreSerializer(serializers.Serializer):
    """Serializer لاستعادة نسخة احتياطية"""
    
    backup_id = serializers.UUIDField()
    restore_type = serializers.ChoiceField(
        choices=['database', 'files', 'full'],
        default='full'
    )














