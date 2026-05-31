from django.core.management.base import BaseCommand
from django.db import connection
from apps.medicines.models import Medicine


class Command(BaseCommand):
    help = 'Remove duplicate medicines (same name+brand+generic_name), keeping the oldest (lowest id)'

    def handle(self, *args, **options):
        total_before = Medicine.objects.count()
        self.stdout.write(f'Medicines before dedup: {total_before}')

        # Raw SQL: single DELETE removing all duplicates, keeping MIN(id) per group
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM medicines_medicine
                WHERE id NOT IN (
                    SELECT keep_id FROM (
                        SELECT MIN(id) AS keep_id
                        FROM medicines_medicine
                        GROUP BY name, brand, generic_name
                    ) kept
                )
            """)
            deleted = cursor.rowcount

        total_after = Medicine.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'Done! Deleted {deleted} duplicate records. '
            f'Remaining: {total_after}'
        ))