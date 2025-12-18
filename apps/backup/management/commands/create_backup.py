from django.core.management.base import BaseCommand
from apps.backup.services import BackupService


class Command(BaseCommand):
    help = 'إنشاء نسخة احتياطية يدوية'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['database', 'files', 'full'],
            default='full',
            help='نوع النسخة الاحتياطية (database, files, full)'
        )
        parser.add_argument(
            '--description',
            type=str,
            default=None,
            help='وصف النسخة الاحتياطية'
        )

    def handle(self, *args, **options):
        backup_type = options['type']
        description = options['description']
        
        self.stdout.write(f'بدء إنشاء نسخة احتياطية من نوع: {backup_type}')
        
        service = BackupService()
        
        if backup_type == 'database':
            result = service.backup_database()
            if result['success']:
                self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء نسخة احتياطية لقاعدة البيانات: {result["path"]}'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ فشل إنشاء النسخة الاحتياطية: {result.get("error")}'))
        
        elif backup_type == 'files':
            result = service.backup_files()
            if result['success']:
                self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء نسخة احتياطية للملفات: {result["path"]}'))
            else:
                self.stdout.write(self.style.ERROR(f'✗ فشل إنشاء النسخة الاحتياطية: {result.get("error")}'))
        
        else:  # full
            backup = service.create_full_backup(description=description)
            if backup.is_completed:
                self.stdout.write(self.style.SUCCESS(f'✓ تم إنشاء نسخة احتياطية كاملة بنجاح'))
                self.stdout.write(f'  - قاعدة البيانات: {backup.database_size} bytes')
                self.stdout.write(f'  - الملفات: {backup.files_size} bytes')
                self.stdout.write(f'  - الإجمالي: {backup.total_size} bytes')
            else:
                self.stdout.write(self.style.ERROR(f'✗ فشل إنشاء النسخة الاحتياطية: {backup.error_message}'))














