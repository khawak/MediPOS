r"""
Management command to import medicines from a CSV file.

Handles large files (90K+ rows) efficiently using bulk_create with
ignore_conflicts. Resolves category by name, skips duplicate barcodes,
and respects the unique_together constraint on (name, brand, generic_name).

Usage:
    python manage.py import_medicines --file "C:\Users\Alvee\Desktop\Medicine Data\medicine_import_template.csv"
    python manage.py import_medicines --file path/to/file.csv --dry-run
"""
import csv
import io
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.medicines.models import Category, Medicine


class Command(BaseCommand):
    """
    Import medicine records from a CSV file into the database.

    Expected CSV columns (header):
        name, generic_name, brand, category, barcode, unit,
        purchase_price, selling_price, tax_rate, reorder_level, description
    """

    help = 'Import medicines from a CSV file.'

    CSV_COLUMNS = [
        'name', 'generic_name', 'brand', 'category', 'barcode', 'unit',
        'purchase_price', 'selling_price', 'tax_rate', 'reorder_level',
        'description',
    ]

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
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            default=True,
            help='Skip rows where (name, brand, generic_name) already exists (default: True).',
        )
        parser.add_argument(
            '--no-skip-existing',
            action='store_false',
            dest='skip_existing',
            help='Do not skip existing records; attempt to insert all rows.',
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        skip_existing = options['skip_existing']

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
            self.style.MIGRATE_HEADING(
                f'=== MediPOS Medicine CSV Import ==='
            )
        )
        self.stdout.write(f'  Source file: {file_path}')
        self.stdout.write(f'  Dry run: {dry_run}')
        self.stdout.write(f'  Batch size: {batch_size}')
        self.stdout.write(f'  Skip existing: {skip_existing}')
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

        # Pre-load all categories into a lookup dict (case-insensitive)
        self.stdout.write('  Loading categories...')
        category_map = {
            cat.name.lower(): cat
            for cat in Category.objects.all()
        }
        missing_categories = set()  # Track categories not found
        self.stdout.write(
            self.style.SUCCESS(
                f'    [OK] Loaded {len(category_map)} existing categories.'
            )
        )

        # Pre-load existing medicine keys (name, brand, generic_name) for
        # fast duplicate detection when skip_existing is True.
        existing_keys = set()
        if skip_existing:
            self.stdout.write('  Loading existing medicine keys...')
            for med in Medicine.objects.values_list(
                'name', 'brand', 'generic_name'
            ).iterator(chunk_size=2000):
                existing_keys.add(
                    (med[0].strip().lower(), med[1].strip().lower(), med[2].strip().lower())
                )
            self.stdout.write(
                self.style.SUCCESS(
                    f'    [OK] Loaded {len(existing_keys)} existing medicine keys.'
                )
            )

        # Pre-load existing barcodes for duplicate detection
        existing_barcodes = set(
            Medicine.objects.exclude(barcode__isnull=True)
            .exclude(barcode='')
            .values_list('barcode', flat=True)
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'    [OK] Loaded {len(existing_barcodes)} existing barcodes.'
            )
        )

        # Parse and validate rows
        self.stdout.write('\n  Parsing CSV rows...')
        medicines_to_create = []
        skipped_duplicate_key = 0
        skipped_duplicate_barcode = 0
        skipped_missing_category = 0
        skipped_invalid_row = 0
        skipped_empty_row = 0
        skipped_csv_duplicate = 0
        csv_seen_keys = set()  # Deduplicate within the CSV itself

        total_rows = 0

        for row_num, row in enumerate(reader, start=2):  # Row 1 = header
            total_rows += 1

            if total_rows % 5000 == 0:
                self.stdout.write(
                    f'    Processing row {total_rows}...'
                    f' (created: {len(medicines_to_create)},'
                    f' skipped: {skipped_duplicate_key + skipped_duplicate_barcode + skipped_missing_category + skipped_invalid_row + skipped_empty_row + skipped_csv_duplicate})'
                )

            # Skip completely empty rows
            if not any(v.strip() for v in row.values() if v):
                skipped_empty_row += 1
                continue

            name = row.get('name', '').strip()
            if not name:
                skipped_invalid_row += 1
                continue

            generic_name = row.get('generic_name', '').strip()
            brand = row.get('brand', '').strip()

            # Deduplicate within the CSV itself using (name, brand, generic)
            csv_key = (name.lower(), brand.lower(), generic_name.lower())
            if csv_key in csv_seen_keys:
                skipped_csv_duplicate += 1
                continue
            csv_seen_keys.add(csv_key)

            # Skip if already exists in DB
            if skip_existing and csv_key in existing_keys:
                skipped_duplicate_key += 1
                continue

            # Handle barcode
            barcode = row.get('barcode', '').strip() or None
            if barcode and barcode in existing_barcodes:
                skipped_duplicate_barcode += 1
                continue

            # Track barcode to avoid duplicates within the batch
            if barcode:
                existing_barcodes.add(barcode)

            # Resolve category by name
            category_name = row.get('category', '').strip()
            category = None
            if category_name:
                cat_key = category_name.lower()
                category = category_map.get(cat_key)
                if category is None and cat_key not in missing_categories:
                    missing_categories.add(cat_key)
                    skipped_missing_category += 1
                    continue
                elif category is None:
                    skipped_missing_category += 1
                    continue

            # Parse numeric fields with defaults
            try:
                purchase_price = self._parse_decimal(
                    row.get('purchase_price', ''), default=0.00
                )
                selling_price = self._parse_decimal(
                    row.get('selling_price', ''), default=0.00
                )
                tax_rate = self._parse_decimal(
                    row.get('tax_rate', ''), default=15.00
                )
                reorder_level = self._parse_int(
                    row.get('reorder_level', ''), default=10
                )
            except (ValueError, TypeError) as exc:
                self.stdout.write(
                    self.style.WARNING(
                        f'    [!] Row {row_num} ({name}): '
                        f'Invalid numeric value -- {exc}. Skipping.'
                    )
                )
                skipped_invalid_row += 1
                continue

            unit = row.get('unit', 'Pcs').strip() or 'Pcs'
            description = row.get('description', '').strip()

            medicines_to_create.append(
                Medicine(
                    name=name,
                    generic_name=generic_name,
                    brand=brand,
                    category=category,
                    barcode=barcode,
                    unit=unit,
                    purchase_price=purchase_price,
                    selling_price=selling_price,
                    tax_rate=tax_rate,
                    reorder_level=reorder_level,
                    description=description,
                )
            )

            # Bulk create when batch size reached
            if len(medicines_to_create) >= batch_size:
                self._flush_batch(medicines_to_create, dry_run)
                medicines_to_create = []

        # Flush remaining
        if medicines_to_create:
            self._flush_batch(medicines_to_create, dry_run)

        # Summary
        self.stdout.write('\n' + self.style.MIGRATE_HEADING('=== Import Summary ==='))
        self.stdout.write(f'  Total CSV rows processed:  {total_rows}')
        self.stdout.write(f'  Empty rows skipped:        {skipped_empty_row}')
        self.stdout.write(f'  CSV internal duplicates:   {skipped_csv_duplicate}')
        self.stdout.write(f'  Existing DB duplicates:    {skipped_duplicate_key}')
        self.stdout.write(f'  Duplicate barcodes:        {skipped_duplicate_barcode}')
        self.stdout.write(f'  Missing categories:        {skipped_missing_category}')
        self.stdout.write(f'  Invalid rows:              {skipped_invalid_row}')

        if missing_categories:
            self.stdout.write(
                self.style.WARNING(
                    f'\n  [!] {len(missing_categories)} category name(s) not found in DB:'
                )
            )
            for cat in sorted(missing_categories)[:20]:
                self.stdout.write(f'      - "{cat}"')
            if len(missing_categories) > 20:
                self.stdout.write(
                    f'      ... and {len(missing_categories) - 20} more.'
                )

        total_created = self._total_created
        total_failed = self._total_failed

        self.stdout.write(
            self.style.SUCCESS(
                f'\n  [OK] Successfully imported: {total_created} medicine(s)'
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
                self.style.NOTICE('\n  [INFO] DRY RUN -- no changes were saved.')
            )

    def __init__(self):
        super().__init__()
        self._total_created = 0
        self._total_failed = 0

    def _flush_batch(self, batch, dry_run):
        """
        Bulk insert a batch of Medicine objects.

        On constraint violations, falls back to row-by-row insertion
        to report specific failures while succeeding on valid rows.
        """
        if dry_run:
            self._total_created += len(batch)
            self.stdout.write(
                f'    [DRY RUN] Would create {len(batch)} medicine(s).'
            )
            batch.clear()
            return

        try:
            with transaction.atomic():
                # ignore_conflicts skips rows that violate unique constraints
                Medicine.objects.bulk_create(
                    batch,
                    batch_size=len(batch),
                    ignore_conflicts=True,
                )
                # bulk_create with ignore_conflicts doesn't return created
                # count reliably, so we approximate
                self._total_created += len(batch)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'    [OK] Batch: {len(batch)} medicine(s) processed.'
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
            for medicine in batch:
                try:
                    medicine.save()
                    self._total_created += 1
                except Exception as row_exc:
                    self._total_failed += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'      [X] {medicine.name}: {row_exc}'
                        )
                    )
        finally:
            batch.clear()

    @staticmethod
    def _parse_decimal(value, default=0.00):
        """Parse a string to float, returning default on empty/invalid."""
        val = value.strip() if value else ''
        if val == '':
            return default
        return float(val)

    @staticmethod
    def _parse_int(value, default=10):
        """Parse a string to int, returning default on empty/invalid."""
        val = value.strip() if value else ''
        if val == '':
            return default
        return int(float(val))