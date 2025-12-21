from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Backup


# ============================================================
# Base / Read Serializer
# ============================================================

class BackupSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Backup records.
    Used for listing and detail views.
    """

    created_by = serializers.StringRelatedField(read_only=True)

    duration = serializers.DurationField(read_only=True)
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
            'trigger_source',
            'created_by',

            'database_backup_path',
            'files_backup_path',

            'database_size',
            'files_size',
            'total_size',

            'database_size_display',
            'files_size_display',
            'total_size_display',

            'storage_type',
            'storage_path',

            'description',
            'error_message',

            'created_at',
            'started_at',
            'completed_at',
            'duration',
            'duration_display',
        ]
        read_only_fields = fields

    # --------------------------------------------------------
    # Display Helpers
    # --------------------------------------------------------

    def get_duration_display(self, obj):
        """
        Human-readable duration (Arabic-friendly).
        """
        duration = obj.duration
        if not duration:
            return None

        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}س {minutes}د {seconds}ث"
        if minutes > 0:
            return f"{minutes}د {seconds}ث"
        return f"{seconds}ث"

    def get_database_size_display(self, obj):
        return self._format_size(obj.database_size)

    def get_files_size_display(self, obj):
        return self._format_size(obj.files_size)

    def get_total_size_display(self, obj):
        return self._format_size(obj.total_size)

    # --------------------------------------------------------
    # Internal Utility
    # --------------------------------------------------------

    def _format_size(self, size_bytes: int) -> str:
        if not size_bytes:
            return "0 B"

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        index = 0

        while size >= 1024 and index < len(units) - 1:
            size /= 1024
            index += 1

        return f"{size:.2f} {units[index]}"


# ============================================================
# Create Backup Serializer
# ============================================================

class BackupCreateSerializer(serializers.Serializer):
    """
    Serializer for requesting a new backup operation.

    Actual execution is handled asynchronously (Celery / Task).
    """

    backup_type = serializers.ChoiceField(
        choices=Backup.BackupType.choices,
        default=Backup.BackupType.FULL,
        label=_("Backup Type")
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        label=_("Description / Notes")
    )

    trigger_source = serializers.ChoiceField(
        choices=Backup.TriggerSource.choices,
        default=Backup.TriggerSource.MANUAL,
        label=_("Trigger Source")
    )


# ============================================================
# Restore Backup Serializer
# ============================================================

class BackupRestoreSerializer(serializers.Serializer):
    """
    Serializer for restoring a backup.
    """

    backup_id = serializers.UUIDField(
        label=_("Backup ID")
    )

    restore_type = serializers.ChoiceField(
        choices=Backup.BackupType.choices,
        default=Backup.BackupType.FULL,
        label=_("Restore Type")
    )


# ============================================================
# Internal Status Update Serializer (System Use)
# ============================================================

class BackupStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Internal serializer for updating backup execution status.
    Intended for background tasks only.
    """

    class Meta:
        model = Backup
        fields = [
            'status',
            'database_backup_path',
            'files_backup_path',
            'database_size',
            'files_size',
            'total_size',
            'error_message',
            'started_at',
            'completed_at',
        ]
