import logging

from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import Role
from apps.audit.services import log_audit_event
from .permissions import IsTechSupport

from .models import Backup
from .serializers import (
    BackupSerializer,
    BackupCreateSerializer,
    BackupRestoreSerializer,
)
from .services import create_backup, mark_backup_failed, restore_backup
from .tasks import run_backup_task

logger = logging.getLogger(__name__)


class BackupViewSet(GenericViewSet):
    """
    Backup management endpoints.

    - IT Support only
    - Action-based (not CRUD)
    """

    permission_classes = [IsAuthenticated, IsTechSupport]
    serializer_class = BackupSerializer
    queryset = Backup.objects.all().order_by("-created_at")

    # =========================
    # Queryset Scope
    # =========================
    def get_queryset(self):
        user = self.request.user
        role_name = getattr(getattr(user, "role", None), "name", None)
        return self.queryset if role_name == Role.TECH_SUPPORT else self.queryset.none()

    # =========================
    # Actions
    # =========================

    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        """
        List backup history (IT Support only).
        """
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="run")
    def run_backup(self, request):
        """
        Trigger manual backup.
        """
        serializer = BackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            backup = create_backup(
                actor=request.user,
                backup_type=serializer.validated_data["backup_type"],
                description=serializer.validated_data.get("description"),
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Backup creation failed")
            log_audit_event(
                user=request.user,
                action="backup.create.failed",
                description="Backup creation failed.",
            )
            return Response(
                {
                    "detail": "Backup request failed to start.",
                    "error": "Backup request failed to start.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # A request is not accepted unless the worker actually accepted it.
        # Leaving an ``in_progress`` backup after broker failure is misleading
        # and used to be recorded as a successful initiation.
        try:
            run_backup_task.delay(str(backup.id))
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Backup task dispatch failed")
            mark_backup_failed(backup, "Backup worker dispatch failed.")
            log_audit_event(
                user=request.user,
                action="backup.task.dispatch_failed",
                description="Backup task dispatch failed.",
                content_object=backup,
            )
            return Response(
                {"detail": "Backup worker is unavailable. No backup was started.", "backup_id": backup.id},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        log_audit_event(
            user=request.user,
            action="backup.manual.triggered",
            description="Manual backup triggered",
            content_object=backup,
        )

        return Response(
            {
                "backup_id": backup.id,
                "status": backup.status,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """
        Restore a backup.
        """
        backup = self.get_object()

        serializer = BackupRestoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_backup_id = serializer.validated_data.get("backup_id")
        if requested_backup_id and requested_backup_id != backup.id:
            return Response({"detail": "backup_id does not match the URL."}, status=status.HTTP_400_BAD_REQUEST)

        restore_backup(
            actor=request.user,
            backup=backup,
            restore_type=serializer.validated_data["restore_type"],
        )

        log_audit_event(
            user=request.user,
            action="backup.restored",
            description="Backup restored",
            content_object=backup,
        )

        return Response({"status": "restored"}, status=status.HTTP_200_OK)
