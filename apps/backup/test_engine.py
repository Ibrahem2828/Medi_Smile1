import json
import shutil
import uuid
import zipfile
from pathlib import Path

from django.conf import settings
from django.test import TransactionTestCase, override_settings

from apps.backup.engine import BackupEngine, BackupIntegrityError
from apps.backup.models import Backup


class VerifiedBackupEngineTests(TransactionTestCase):
    def setUp(self):
        runtime_root = Path(settings.BASE_DIR) / "test-backup-runtime"
        runtime_root.mkdir(exist_ok=True)
        # Give every test an isolated directory.  Windows can retain a short
        # lived handle to a SQLite backup, so reusing one fixed directory made
        # a later test depend on cleanup timing from an earlier one.
        self.tempdir = runtime_root / str(uuid.uuid4())
        self.tempdir.mkdir()
        root = self.tempdir
        self.private_media = root / "private-media"
        self.public_media = root / "media"
        self.private_media.mkdir(exist_ok=True)
        self.public_media.mkdir(exist_ok=True)
        self.settings_override = override_settings(
            BACKUP_DIRECTORY=str(root / "backups"),
            BACKUP_STORAGE_TYPE="local",
            PRIVATE_MEDIA_ROOT=self.private_media,
            MEDIA_ROOT=self.public_media,
        )
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.tempdir, ignore_errors=True)
        super().tearDown()

    def test_database_backup_is_a_real_verified_sqlite_database(self):
        backup = Backup.objects.create(backup_type=Backup.BackupType.DATABASE)
        engine = BackupEngine()
        engine.backup_database(backup)

        backup.refresh_from_db()
        artifact = Path(backup.database_backup_path)
        self.assertEqual(artifact.suffix, ".sqlite3")
        self.assertGreater(artifact.stat().st_size, 21)
        engine.verify_database_backup(artifact)

    def test_files_backup_has_a_checksum_manifest_and_is_a_valid_zip(self):
        clinical_file = self.private_media / "dental" / "xray.jpg"
        clinical_file.parent.mkdir()
        clinical_file.write_bytes(b"synthetic-clinical-image")
        backup = Backup.objects.create(backup_type=Backup.BackupType.FILES)

        engine = BackupEngine()
        engine.backup_files(backup)

        backup.refresh_from_db()
        artifact = Path(backup.files_backup_path)
        engine.verify_files_backup(artifact)
        with zipfile.ZipFile(artifact) as archive:
            manifest = json.loads(archive.read("_manifest.json"))
        self.assertIn("private/dental/xray.jpg", manifest)

    def test_restore_is_disabled_until_an_isolated_target_is_configured(self):
        backup = Backup.objects.create(backup_type=Backup.BackupType.DATABASE)
        engine = BackupEngine()
        engine.backup_database(backup)
        with self.assertRaises(BackupIntegrityError):
            engine.restore_database(backup.database_backup_path)
