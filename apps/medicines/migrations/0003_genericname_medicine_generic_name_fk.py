from django.db import migrations, models
import django.db.models.deletion


def _populate_generic_names(apps, schema_editor):
    """
    For every distinct non-blank generic_name string on Medicine,
    create a GenericName row, then point medicine.generic_name_fk at it.
    """
    Medicine = apps.get_model('medicines', 'Medicine')
    GenericName = apps.get_model('medicines', 'GenericName')

    # Collect distinct non-blank values
    names = (
        Medicine.objects
        .exclude(generic_name='')
        .values_list('generic_name', flat=True)
        .distinct()
    )

    # Bulk-create GenericName rows (ignore conflicts in case of re-run)
    for name in names:
        stripped = name.strip()
        if stripped:
            GenericName.objects.get_or_create(name=stripped)

    # Now point every medicine FK at its matching GenericName
    for medicine in Medicine.objects.exclude(generic_name=''):
        stripped = medicine.generic_name.strip()
        if stripped:
            try:
                gn = GenericName.objects.get(name=stripped)
                medicine.generic_name_fk = gn
                medicine.save(update_fields=['generic_name_fk'])
            except GenericName.DoesNotExist:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('medicines', '0002_alter_medicine_unique_together'),
    ]

    operations = [
        # 1. Create GenericName table
        migrations.CreateModel(
            name='GenericName',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='International non-proprietary name (INN) of the drug.', max_length=200, unique=True, verbose_name='name')),
                ('description', models.TextField(blank=True, verbose_name='description')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
            ],
            options={
                'verbose_name': 'Generic Name',
                'verbose_name_plural': 'Generic Names',
                'ordering': ['name'],
            },
        ),

        # 2. Add a temporary nullable FK column alongside the old CharField
        migrations.AddField(
            model_name='medicine',
            name='generic_name_fk',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='medicines.genericname',
                verbose_name='generic name (fk)',
            ),
        ),

        # 3. Data migration: populate GenericName rows and wire FK
        migrations.RunPython(
            _populate_generic_names,
            reverse_code=migrations.RunPython.noop,
        ),

        # 4. Drop old unique_together (references CharField 'generic_name')
        migrations.AlterUniqueTogether(
            name='medicine',
            unique_together=set(),
        ),

        # 5. Remove the old CharField
        migrations.RemoveField(
            model_name='medicine',
            name='generic_name',
        ),

        # 6. Rename temp FK column to generic_name
        migrations.RenameField(
            model_name='medicine',
            old_name='generic_name_fk',
            new_name='generic_name',
        ),

        # 7. Restore unique_together on the FK field
        migrations.AlterUniqueTogether(
            name='medicine',
            unique_together={('name', 'brand', 'generic_name')},
        ),
    ]
