# apps/backup/engine.py
import os
from django.conf import settings
from django.utils import timezone


class BackupEngine:
    """
    Low-level backup executor (DB + Files).
    No permissions, no audit, no API logic here.
    """

    storage_type = "local"

    def __init__(self):
        self.backup_directory = os.path.join(
            settings.BASE_DIR,
            "backups",
            timezone.now().strftime("%Y/%m/%d"),
        )
        os.makedirs(self.backup_directory, exist_ok=True)

    # ============================
    # Database
    # ============================

    def backup_database(self, backup):
        path = os.path.join(self.backup_directory, f"db_{backup.id}.sql")
        # ⚠️ مثال فقط – لاحقًا pg_dump / mysqldump
        with open(path, "w") as f:
            f.write("-- database backup --")

        backup.database_backup_path = path
        backup.database_size = os.path.getsize(path)
        backup.save(update_fields=["database_backup_path", "database_size"])

    def restore_database(self, path: str):
        # TODO: restore logic
        pass

    # ============================
    # Files
    # ============================

    def backup_files(self, backup):
        path = os.path.join(self.backup_directory, f"files_{backup.id}.zip")
        with open(path, "w") as f:
            f.write("files backup")

        backup.files_backup_path = path
        backup.files_size = os.path.getsize(path)
        backup.save(update_fields=["files_backup_path", "files_size"])

    def restore_files(self, path: str):
        # TODO: restore logic
        pass
