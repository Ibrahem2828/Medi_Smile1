from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from django.shortcuts import get_object_or_404
from django.db.models import Sum

import logging

from .models import Backup
from .serializers import (
    BackupSerializer,
    BackupCreateSerializer,
    BackupRestoreSerializer,
)
from .services import BackupService
from .tasks import create_backup_task

logger = logging.getLogger(__name__)


# ============================================================
# Backup ViewSet
# ============================================================

class BackupViewSet(viewsets.ModelViewSet):
    """
    Backup Management API.

    Features:
    - List backups
    - Create backup (async / sync)
    - Restore backup
    - Statistics
    - Cleanup old backups

    Access:
    - Admin / Tech Support only
    """

    queryset = Backup.objects.all()
    serializer_class = BackupSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    # --------------------------------------------------------
    # Queryset
    # --------------------------------------------------------

    def get_queryset(self):
        queryset = super().get_queryset()

        backup_type = self.request.query_params.get("type")
        status_filter = self.request.query_params.get("status")

        if backup_type:
            queryset = queryset.filter(backup_type=backup_type)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by("-created_at")

    # --------------------------------------------------------
    # Async Backup (Recommended)
    # --------------------------------------------------------

    @action(detail=False, methods=["post"], url_path="create")
    def create_backup(self, request):
        """
        Create backup asynchronously (Celery).

        Recommended for production usage.
        """
        serializer = BackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        backup_type = serializer.validated_data.get("backup_type", "full")
        description = serializer.validated_data.get("description")

        task = create_backup_task.delay(
            backup_type=backup_type,
            description=description,
            user_id=request.user.id,
        )

        return Response(
            {
                "message": "Backup process started successfully.",
                "task_id": task.id,
                "backup_type": backup_type,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # --------------------------------------------------------
    # Sync Backup (Manual / Debug)
    # --------------------------------------------------------

    @action(detail=False, methods=["post"], url_path="create-sync")
    def create_backup_sync(self, request):
        """
        Create backup synchronously.

        ⚠️ Use only for debugging or controlled environments.
        """
        serializer = BackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        backup_type = serializer.validated_data.get("backup_type", "full")
        description = serializer.validated_data.get("description")

        service = BackupService()

        try:
            if backup_type == Backup.BackupType.DATABASE:
                backup = Backup.objects.create(
                    backup_type=Backup.BackupType.DATABASE,
                    status=Backup.Status.IN_PROGRESS,
                    created_by=request.user,
                    description=description,
                )
                service.backup_database(backup)

            elif backup_type == Backup.BackupType.FILES:
                backup = Backup.objects.create(
                    backup_type=Backup.BackupType.FILES,
                    status=Backup.Status.IN_PROGRESS,
                    created_by=request.user,
                    description=description,
                )
                service.backup_files(backup)

            else:
                backup = service.create_full_backup(
                    created_by=request.user,
                    description=description,
                )

            return Response(
                BackupSerializer(backup).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as exc:
            logger.exception("Backup sync creation failed")
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # --------------------------------------------------------
    # Restore Backup
    # --------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="restore")
    def restore_backup(self, request, pk=None):
        """
        Restore backup (database / files / full).
        """
        backup = get_object_or_404(Backup, pk=pk)

        serializer = BackupRestoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        restore_type = serializer.validated_data.get("restore_type", "full")

        if backup.status != Backup.Status.COMPLETED:
            return Response(
                {"error": "Backup must be completed before restore."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = BackupService()

        try:
            if restore_type in ["database", "full"]:
                if not backup.database_backup_path:
                    return Response(
                        {"error": "Database backup not found."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                result = service.restore_database(backup.database_backup_path)
                if not result["success"]:
                    return Response(
                        {"error": result.get("error")},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            if restore_type in ["files", "full"]:
                if not backup.files_backup_path:
                    return Response(
                        {"error": "Files backup not found."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                result = service.restore_files(backup.files_backup_path)
                if not result["success"]:
                    return Response(
                        {"error": result.get("error")},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            return Response(
                {
                    "message": "Backup restored successfully.",
                    "restore_type": restore_type,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            logger.exception("Restore failed")
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """
        Backup statistics overview.
        """
        qs = Backup.objects.all()

        total_size = qs.filter(
            status=Backup.Status.COMPLETED
        ).aggregate(total=Sum("total_size"))["total"] or 0

        latest_backup = qs.filter(
            status=Backup.Status.COMPLETED
        ).first()

        return Response(
            {
                "total_backups": qs.count(),
                "completed": qs.filter(status=Backup.Status.COMPLETED).count(),
                "failed": qs.filter(status=Backup.Status.FAILED).count(),
                "in_progress": qs.filter(status=Backup.Status.IN_PROGRESS).count(),
                "total_size": total_size,
                "total_size_display": self._format_size(total_size),
                "latest_backup": BackupSerializer(latest_backup).data
                if latest_backup else None,
            },
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------

    @action(detail=False, methods=["post"], url_path="cleanup")
    def cleanup(self, request):
        """
        Cleanup old backups.
        """
        days_to_keep = int(request.data.get("days_to_keep", 30))

        service = BackupService()
        result = service.cleanup_old_backups(days_to_keep=days_to_keep)

        if result["success"]:
            return Response(
                {
                    "message": f"Deleted {result['deleted_count']} old backups."
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": result.get("error")},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # --------------------------------------------------------
    # Utils
    # --------------------------------------------------------

    def _format_size(self, size_bytes: int) -> str:
        if not size_bytes:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        index = 0

        while size >= 1024 and index < len(units) - 1:
            size /= 1024
            index += 1

        return f"{size:.2f} {units[index]}"
