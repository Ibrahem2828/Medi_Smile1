from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import Role
from apps.audit.services import log_audit_event

from .models import Backup
from .serializers import (
    BackupSerializer,
    BackupCreateSerializer,
    BackupRestoreSerializer,
)
from .services import create_backup, restore_backup
from .tasks import run_backup_task


class BackupViewSet(GenericViewSet):
    """
    Backup management endpoints.

    - IT Support only
    - Action-based (not CRUD)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = BackupSerializer
    queryset = Backup.objects.all().order_by("-created_at")

    # =========================
    # Queryset Scope
    # =========================
    def get_queryset(self):
        user = self.request.user
        if user.role.name == Role.TECH_SUPPORT:
            return self.queryset
        return self.queryset.none()

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
        if request.user.role.name != Role.TECH_SUPPORT:
            return Response(
                {"detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BackupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        backup = create_backup(
            actor=request.user,
            backup_type=serializer.validated_data["backup_type"],
            description=serializer.validated_data.get("description"),
        )

        # Run async task
        run_backup_task.delay(str(backup.id))

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
        if request.user.role.name != Role.TECH_SUPPORT:
            return Response(
                {"detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        backup = self.get_object()

        serializer = BackupRestoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

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
