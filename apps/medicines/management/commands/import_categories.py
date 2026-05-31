r"""
Management command to import categories from a CSV file.

Handles bulk import of Category records efficiently using bulk_create with
ignore_conflicts. Resolves duplicates by name, auto-generates slugs.

Usage:
    python manage.py import_categories --file "path/to/categories.csv"
    python manage.py import_categories --file path/to/file.csv --dry-run
"""
import csv
import io
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.medicines.models import Category


class Command(BaseCommand):
    """
    Import category records from a CSV file into the database.

    Expected CSV columns (header):
        name, description, is_active
    """

    help = 'Import categories from a CSV file.'

    CSV_COLUMNS = ['name', 'description', 'is_active']

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to the CSV file to import.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Validate and report without saving to the database.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Number of records per bulk insert batch (default: 500).',
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        if not file_path.exists():
            self.stderr.write(
                self.style.ERROR(f'File not found: {file_path}')
            )
            return

        if not file_path.suffix.lower() == '.csv':
            self.stderr.write(
                self.style.WARNING(
                    f'File does not have a .csv extension: {file_path}. '
                    'Attempting to read anyway.'
                )
            )

        self.stdout.write(
            self.style.MIGRATE_HEADING('=== MediPOS Category CSV Import ===')
        )
        self.stdout.write(f'  Source file: {file_path}')
        self.stdout.write(f'  Dry run: {dry_run}')
        self.stdout.write(f'  Batch size: {batch_size}')
        self.stdout.write('')

        # Read the CSV content
        self.stdout.write('  Reading CSV file...')
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()

        reader = csv.DictReader(io.StringIO(content))

        # Pre-load existing category names for duplicate detection (case-insensitive)
        self.stdout.write('  Loading existing categories...')
        existing_names = set(
            Category.objects.values_list('name', flat=True)
        )
        existing_names_lower = {n.lower() for n in existing_names}
        self.stdout.write(
            self.style.SUCCESS(
                f'    [OK] Loaded {len(existing_names)} existing categories.'
            )
        )

        # Parse and validate rows
        self.stdout.write('\n  Parsing CSV rows...')
        categories_to_create = []
        skipped_duplicate_name = 0
        skipped_empty_name = 0
        skipped_invalid_row = 0
        skipped_empty_row = 0
        skipped_csv_duplicate = 0
        csv_seen_names = set()  # Deduplicate within the CSV itself

        total_rows = 0

        for row_num, row in enumerate(reader, start=2):  # Row 1 = header
            total_rows += 1

            if total_rows % 5000 == 0:
                self.stdout.write(
                    f'    Processing row {total_rows}...'
                    f' (to create: {len(categories_to_create)},'
                    f' skipped: {skipped_duplicate_name + skipped_empty_name + skipped_invalid_row + skipped_empty_row + skipped_csv_duplicate})'
                )

            # Skip completely empty rows
            if not any(v.strip() for v in row.values() if v):
                skipped_empty_row += 1
                continue

            name = row.get('name', '').strip()
            if not name:
                skipped_empty_name += 1
                continue

            # Deduplicate within the CSV itself (case-insensitive)
            name_lower = name.lower()
            if name_lower in csv_seen_names:
                skipped_csv_duplicate += 1
                continue
            csv_seen_names.add(name_lower)

            # Skip if already exists in DB (case-insensitive)
            if name_lower in existing_names_lower:
                skipped_duplicate_name += 1
                continue

            # Parse optional fields
            description = row.get('description', '').strip()
            is_active_str = row.get('is_active', 'true').strip().lower()
            is_active = is_active_str in ('true', '1', 'yes', 'y')

            categories_to_create.append(
                Category(
                    name=name,
                    slug=slugify(name),
                    description=description,
                    is_active=is_active,
                )
            )

            # Bulk create when batch size reached
            if len(categories_to_create) >= batch_size:
                self._flush_batch(categories_to_create, dry_run)
                categories_to_create = []

        # Flush remaining
        if categories_to_create:
            self._flush_batch(categories_to_create, dry_run)

        # Summary
        self.stdout.write(
            '\n' + self.style.MIGRATE_HEADING('=== Import Summary ===')
        )
        self.stdout.write(f'  Total CSV rows processed:  {total_rows}')
        self.stdout.write(f'  Empty rows skipped:        {skipped_empty_row}')
        self.stdout.write(f'  CSV internal duplicates:   {skipped_csv_duplicate}')
        self.stdout.write(f'  Existing DB duplicates:    {skipped_duplicate_name}')
        self.stdout.write(f'  Rows with empty name:      {skipped_empty_name}')
        self.stdout.write(f'  Invalid rows:              {skipped_invalid_row}')

        total_created = self._total_created
        total_failed = self._total_failed

        self.stdout.write(
            self.style.SUCCESS(
                f'\n  [OK] Successfully imported: {total_created} category/categories'
            )
        )
        if total_failed:
            self.stdout.write(
                self.style.WARNING(
                    f'  [!] Failed (DB constraint): {total_failed} row(s)'
                )
            )
        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    '\n  [INFO] DRY RUN -- no changes were saved.'
                )
            )

    def __init__(self):
        super().__init__()
        self._total_created = 0
        self._total_failed = 0

    def _flush_batch(self, batch, dry_run):
        """
        Bulk insert a batch of Category objects.

        Falls back to row-by-row insertion on constraint violations
        to report specific failures while succeeding on valid rows.
        """
        if dry_run:
            self._total_created += len(batch)
            self.stdout.write(
                f'    [DRY RUN] Would create {len(batch)} category/categories.'
            )
            batch.clear()
            return

        try:
            with transaction.atomic():
                Category.objects.bulk_create(
                    batch,
                    batch_size=len(batch),
                    ignore_conflicts=True,
                )
                self._total_created += len(batch)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'    [OK] Batch: {len(batch)} category/categories processed.'
                    )
                )
        except Exception as exc:
            # Fallback: try row-by-row for this batch
            self.stdout.write(
                self.style.WARNING(
                    f'    [!] Batch insert failed ({exc}). '
                    'Trying row-by-row...'
                )
            )
            for category in batch:
                try:
                    category.save()
                    self._total_created += 1
                except Exception as row_exc:
                    self._total_failed += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'      [X] {category.name}: {row_exc}'
                        )
                    )
        finally:
            batch.clear()